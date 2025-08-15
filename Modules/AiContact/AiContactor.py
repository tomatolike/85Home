from openai import OpenAI
from Core.utility import get_logger
import os
import json
import time

class AiContactor:
    def __init__(self, mode="DEEPSEEK", key=""):
        self.logger = get_logger(__name__)
        self.open_ai_api_key = key
        self.deep_seek_api_key = key
        self.mode = mode
        self.client = None
        if self.mode == "OPENAI":
            self.client = OpenAI(api_key=self.open_ai_api_key)
        elif self.mode == "DEEPSEEK":
            self.client = OpenAI(api_key=self.deep_seek_api_key, base_url="https://api.deepseek.com")

        self.system_message = ""
        self.message_list = [
        ]

    def parse_response(self, response_text):
        self.logger.info(f"Response from AI model: {response_text}")
        def clean_json_response(text):
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]  # Remove ```json\n
            elif text.startswith("```"):
                text = text[3:]  # Remove ```
            if text.endswith("```"):
                text = text[:-3]
            return text.strip()
        response_text = clean_json_response(response_text)
        response = None
        try:
            response = json.loads(response_text)
        except Exception as e:
            self.logger.error(f"Failed to parse AI response: {e}")
            response = {
                "message": f"Invalid response from AI model. {e}",
                "action": "MessageOnly",
            }
        return response

    def communicate(self, message, from_type=1):
        self.logger.info(f"Send to AI model: {message}")
        response = None
        if self.mode == "OPENAI":
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.generate_messages(message, from_type),
                stream=False
            )
            response = self.parse_response(response.choices[0].message.content)
        elif self.mode == "DEEPSEEK":
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=self.generate_messages(message, from_type),
                stream=False
            )
            response = self.parse_response(response.choices[0].message.content)
        self.generate_messages(json.dumps(response), from_type=2)
        return response
    
    def add_message_history(self, message, role="user"):
        self.message_list.append({
            "time": time.time(),
            "message":{
                "role": role,
                "content": message
            }
        })

    def generate_system_message(self, action_list_info):
        self.system_message = {
            "role": "system",
            "content": (
                "You are a home assistant.\n"
                "I will send you many messages, either from human user's voice or from the system, "
                "and you will respond in a raw json string in the following format:\n"
                "{\n"
                '  "message": "what you want to say to the human user. If you are responding to the system, message should be empty. If you are responding to the human user, this should never be empty.",\n'
                '  "action": "the action you want to do. Pick action name from the available actions below",\n'
                '  "action_params": {} # the parameters for the action, depends on the action type\n'
                "}\n"
                "Your response text must be directly parseable by json.loads in python and it should not be pretty formatted.\n"
                "Human user will speak chinese to you and your message must be in chinese too.\n"
                "The message is decoded by Vosk, so it might not be fully accurate. Try your best effort to understand it.\n"
                "Here are the available actions:\n\n"
                "Action: MessageOnly\n"
                "description: the message will be played to the human user, no other action performed. NEVER return an empty message with MessageOnly action.\n"
                "parameters:\n"
                "- isQuestion: a boolean, whether you are expecting a response or an answer from the human user. You can only use it as true twice in one conversation."
                + action_list_info
            )
        }
        #self.logger.info(f"System message generated: {self.system_message['content']}")
    
    def clean_up_messages(self):
        now = time.time()
        i = 0
        while i < len(self.message_list):
            if now - self.message_list[i]["time"] > 3600:
                self.message_list.pop(i)
            else:
                i += 1

    def generate_messages(self, user_message, from_type):
        sender = "user"
        if from_type == 1:
            pass
        elif from_type == 2:
            sender = "assistant"
        elif from_type == 3:
            sender = "system"
        new_message = {
            "time": time.time(),
            "message":{
                "role": sender,
                "content": user_message
            }
        }
        self.message_list.append(new_message)
        self.clean_up_messages()
        
        final_messages = [self.system_message]
        for msg in self.message_list:
            final_messages.append(msg["message"])
        return final_messages
    
    def get_message_list(self):
        message_list = [{
            "time": time.time(),
            "message":self.system_message
        }]

        message_list += self.message_list
        return message_list

from openai import OpenAI
from Core.utility import get_logger
import os
import json

class AiContactor:
    def __init__(self, mode="DEEPSEEK"):
        self.logger = get_logger(__name__)
        self.open_ai_api_key = "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"
        self.deep_seek_api_key = "sk-fc5a3dbefd0f4171ba455d11bbc6ed11"
        self.mode = mode
        self.client = None
        if self.mode == "OPENAI":
            self.client = OpenAI(api_key=self.open_ai_api_key)
        elif self.mode == "DEEPSEEK":
            self.client = OpenAI(api_key=self.deep_seek_api_key, base_url="https://api.deepseek.com")

        self.system_message = ""
        self.message_list = [self.system_message]

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

    def communicate(self, message, from_user=True):
        self.logger.info(f"Send to AI model: {message}")
        response = None
        if self.mode == "OPENAI":
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.generate_messages(message, from_user),
                stream=False
            )
            response = self.parse_response(response.choices[0].message.content)
        elif self.mode == "DEEPSEEK":
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=self.generate_messages(message, from_user),
                stream=False
            )
            response = self.parse_response(response.choices[0].message.content)
        return response

    def generate_system_message(self, action_list_info):
        self.system_message = {
            "role": "system",
            "content": (
                "You are a home assistant.\n"
                "I will send you many messages, either from human user's voice or from the local agent system, "
                "and you will respond in a raw json string in the following format:\n"
                "{\n"
                '  "message": "what you want to say to the human user, if it\'s responding to the local agent system, this should be empty",\n'
                '  "action": "the action you want to do. Pick action name from the available actions below",\n'
                '  "action_params": {} # the parameters for the action, depends on the action type\n'
                "}\n"
                "Your response text must be directly parseable by json.loads in python and it should not be pretty formatted.\n"
                "Human user will speak chinese to you and your message must be in chinese too.\n"
                "The message is decoded by Vosk, so it might not be fully accurate. Try your best effort to understand it.\n"
                "Here are the available actions:\n\n"
                "Action: MessageOnly\n"
                "description: the message will be played to the human user, no other action performed. If you don't understand the user message, say you don't understand. NEVER return an empty message with MessageOnly action.\n"
                "parameters: none\n"
                + action_list_info
            )
        }
        self.logger.info(f"System message generated: {self.system_message['content']}")
    
    def generate_messages(self, user_message, from_user):
        self.message_list[0] = self.system_message
        new_message = {
            "role": "user" if from_user else "local_agent",
            "content": user_message
        }
        self.message_list.append(new_message)
        if len(self.message_list) > 10:
            self.message_list.pop(1)
        return self.message_list

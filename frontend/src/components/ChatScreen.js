import React, { useState, useRef, useEffect } from 'react';
import './ChatScreen.css';

function ChatScreen({ messages, onSendTask }) {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (inputText.trim()) {
      onSendTask({ type: 'chat_message', text: inputText });
      setInputText('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getMessageBgColor = (role) => {
    switch (role) {
      case 'user':
        return '#bbdefb';
      case 'assistant':
        return '#c8e6c9';
      case 'system':
        return '#e0e0e0';
      default:
        return '#ffffff';
    }
  };

  return (
    <div className="chat-screen">
      <div className="messages-container">
        {messages.map((msg, index) => (
          <div
            key={index}
            className="message"
            style={{
              backgroundColor: getMessageBgColor(msg.role),
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="input-container">
        <input
          type="text"
          className="message-input"
          placeholder="Enter task..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button className="send-button" onClick={handleSend}>
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatScreen;

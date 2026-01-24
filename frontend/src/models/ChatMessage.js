class ChatMessage {
  constructor(role, content) {
    this.role = role;
    this.content = content;
  }

  static fromJson(json) {
    let content = json.content;
    // Try to decode if it's a JSON string
    try {
      const decoded = JSON.parse(content);
      content = JSON.stringify(decoded);
    } catch (e) {
      // If decoding fails, use original content
    }
    return new ChatMessage(json.role, content);
  }
}

export default ChatMessage;

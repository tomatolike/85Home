from VoiceCollector import VoiceCollector
# Example usage
if __name__ == "__main__":
    def print_text(text):
        print("Recognized:", text)

    vc = VoiceCollector()
    vc.SetCallback(print_text)
    vc.Start()

    try:
        print("Listening... Press Ctrl+C to stop.")
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping...")
        vc.Stop()

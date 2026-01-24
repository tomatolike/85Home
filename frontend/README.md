# 85Home Frontend

React web frontend for the 85Home home assistant system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Build for production:
```bash
npm run build
```

3. The built files will be in the `build/` directory, which will be served by the FastAPI server.

## Development

To run the development server:
```bash
npm start
```

This will start the React development server on http://localhost:3000

## Features

- **Chat Screen**: View conversation history and send text messages to the assistant
- **Devices Screen**: View and control smart home devices (Kasa, SwitchBot, Roborock, Whisker)
- **Robot Screen**: Monitor robot status and control robot movement and modes

## API Endpoints

The frontend communicates with the backend via:
- `GET /status` - Fetch current status (messages, devices, robot)
- `POST /task` - Send a task/command to the assistant

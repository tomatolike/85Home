import React, { useState } from 'react';
import './RobotScreen.css';

function RobotScreen({ robotStatuses, onSendTask }) {
  const [pressedButton, setPressedButton] = useState(null);

  const sendMoveCommand = (command) => {
    onSendTask({ type: 'robot_move', command });
  };

  const togglePower = () => {
    onSendTask({ type: 'robot_car', command: 'togglePower' });
  };

  const sendModeCommand = (mode) => {
    onSendTask({ type: 'robot_car', command: mode });
  };

  const sendDockCommand = () => {
    onSendTask({ type: 'robot_car', command: 'dock' });
  };

  const handleMoveButtonDown = (command) => {
    setPressedButton(command);
    sendMoveCommand(command);
  };

  const handleMoveButtonUp = () => {
    if (pressedButton) {
      sendMoveCommand('Stop');
      setPressedButton(null);
    }
  };

  const MoveButton = ({ command, icon, label }) => (
    <div
      className={`move-button ${pressedButton === command ? 'pressed' : ''}`}
      onMouseDown={() => handleMoveButtonDown(command)}
      onMouseUp={handleMoveButtonUp}
      onMouseLeave={handleMoveButtonUp}
      onTouchStart={() => handleMoveButtonDown(command)}
      onTouchEnd={handleMoveButtonUp}
    >
      {icon || label}
    </div>
  );

  return (
    <div className="robot-screen">
      <div className="robot-status-list">
        {robotStatuses.map((status, index) => (
          <div key={index} className="status-item">
            <span className="status-key">{status.key}</span>
            <span className="status-value">{String(status.value)}</span>
          </div>
        ))}
      </div>
      <div className="robot-controls">
        <div className="movement-controls">
          <div className="movement-row">
            <MoveButton command="Left" label="←" />
            <div className="movement-column">
              <MoveButton command="Forward" label="↑" />
              <MoveButton command="Back" label="↓" />
            </div>
            <MoveButton command="Right" label="→" />
          </div>
        </div>
        <div className="mode-controls">
          <button
            className="mode-button"
            onClick={() => sendModeCommand('enterPassiveMode')}
          >
            Passive Mode
          </button>
          <button
            className="mode-button"
            onClick={() => sendModeCommand('enterSafeMode')}
          >
            Safe Mode
          </button>
          <button
            className="mode-button"
            onClick={() => sendModeCommand('enterFullMode')}
          >
            Full Mode
          </button>
        </div>
        <button className="dock-button" onClick={sendDockCommand}>
          Dock
        </button>
        <button className="power-button" onClick={togglePower}>
          ⚡ Toggle Power
        </button>
      </div>
    </div>
  );
}

export default RobotScreen;

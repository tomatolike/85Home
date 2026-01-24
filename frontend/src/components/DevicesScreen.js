import React from 'react';
import './DevicesScreen.css';

function DevicesScreen({ devices, onSendTask }) {
  const parseStatuses = (description) => {
    const regex = /Status (?:could|can) be ([^"]+)/;
    const match = description.match(regex);
    if (match) {
      const statuses = match[1];
      return statuses
        .replace(/or/gi, ',')
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }
    return [];
  };

  return (
    <div className="devices-screen">
      <div className="devices-list">
        {devices.map((device, index) => {
          const possibleStatuses = parseStatuses(device.description);
          return (
            <div key={index} className="device-card">
              <div className="device-header">
                <span className="device-name">{device.alias}</span>
                <span className="device-status">(Status: {device.status})</span>
              </div>
              <div className="device-description">{device.description}</div>
              {possibleStatuses.length > 0 && (
                <div className="device-actions">
                  {possibleStatuses.map((status, statusIndex) => (
                    <button
                      key={statusIndex}
                      className="status-button"
                      onClick={() =>
                        onSendTask({
                          type: 'client_device',
                          target: device.alias,
                          targetStatus: status,
                        })
                      }
                    >
                      {status}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default DevicesScreen;

import React, { useState, useEffect } from 'react';
import './App.css';
import ChatScreen from './components/ChatScreen';
import DevicesScreen from './components/DevicesScreen';
import RobotScreen from './components/RobotScreen';
import ApiService from './services/apiService';
import ChatMessage from './models/ChatMessage';
import Device from './models/Device';
import RobotStatus from './models/RobotStatus';

function App() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [serverAddress, setServerAddress] = useState(
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? `${window.location.hostname}:8080`
      : `${window.location.hostname}${window.location.port ? ':' + window.location.port : ''}`
  );
  const [api, setApi] = useState(new ApiService(`http://${serverAddress}`));
  const [messages, setMessages] = useState([]);
  const [devices, setDevices] = useState([]);
  const [robotStatuses, setRobotStatuses] = useState([]);

  useEffect(() => {
    // Update API service when server address changes
    setApi(new ApiService(`http://${serverAddress}`));
  }, [serverAddress]);

  useEffect(() => {
    // Fetch data periodically
    const fetchData = async () => {
      try {
        const data = await api.fetchStatus();
        setMessages(
          (data.messages || []).map((m) => ChatMessage.fromJson(m.message))
        );
        setDevices((data.devices || []).map((d) => Device.fromJson(d)));
        const robotStatusList = (data.robot?.status || []).map((r) =>
          RobotStatus.fromJson(r)
        );
        if (data.robot) {
          robotStatusList.push(
            new RobotStatus('Connected', data.robot.connected ? 'Yes' : 'No')
          );
        }
        setRobotStatuses(robotStatusList);
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, [api]);

  const handleSendTask = async (task) => {
    try {
      await api.sendTask(task);
      // Refresh data after sending task
      const data = await api.fetchStatus();
      setMessages(
        (data.messages || []).map((m) => ChatMessage.fromJson(m.message))
      );
      setDevices((data.devices || []).map((d) => Device.fromJson(d)));
    } catch (error) {
      console.error('Failed to send task:', error);
    }
  };

  const handleServerAddressChange = (e) => {
    if (e.key === 'Enter') {
      setServerAddress(e.target.value);
    }
  };

  const renderBody = () => {
    switch (selectedTab) {
      case 0:
        return <ChatScreen messages={messages} onSendTask={handleSendTask} />;
      case 1:
        return <DevicesScreen devices={devices} onSendTask={handleSendTask} />;
      case 2:
        return (
          <RobotScreen robotStatuses={robotStatuses} onSendTask={handleSendTask} />
        );
      default:
        return null;
    }
  };

  return (
    <div className="App">
      <div className="app-bar">
        <h1 className="app-title">85Home Client</h1>
        <input
          type="text"
          className="server-input"
          placeholder="Server (ip:port)"
          defaultValue={serverAddress}
          onKeyPress={handleServerAddressChange}
        />
      </div>
      <div className="app-body">{renderBody()}</div>
      <div className="bottom-navigation">
        <button
          className={`nav-button ${selectedTab === 0 ? 'active' : ''}`}
          onClick={() => setSelectedTab(0)}
        >
          💬 Chat
        </button>
        <button
          className={`nav-button ${selectedTab === 1 ? 'active' : ''}`}
          onClick={() => setSelectedTab(1)}
        >
          🏠 Devices
        </button>
        <button
          className={`nav-button ${selectedTab === 2 ? 'active' : ''}`}
          onClick={() => setSelectedTab(2)}
        >
          🤖 Robot
        </button>
      </div>
    </div>
  );
}

export default App;

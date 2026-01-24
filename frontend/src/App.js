import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import ChatScreen from './components/ChatScreen';
import DevicesScreen from './components/DevicesScreen';
import RobotScreen from './components/RobotScreen';
import Screensaver from './components/Screensaver';
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
  const [screensaverActive, setScreensaverActive] = useState(false);
  const [screensaverImages, setScreensaverImages] = useState([]);
  const [screensaverTimeout, setScreensaverTimeout] = useState(5); // Default 5 minutes
  const lastActivityTime = useRef(Date.now());
  const inactivityTimer = useRef(null);
  const countdownTimer = useRef(null);

  useEffect(() => {
    // Update API service when server address changes
    setApi(new ApiService(`http://${serverAddress}`));
  }, [serverAddress]);

  // Load screensaver config and images
  useEffect(() => {
    const loadScreensaverConfig = async () => {
      try {
        // Load config first
        const configResponse = await fetch(`http://${serverAddress}/api/screensaver/config`);
        const configData = await configResponse.json();
        setScreensaverTimeout(configData.timeoutMinutes || 5);
        
        // Then load images
        const imagesResponse = await fetch(`http://${serverAddress}/api/screensaver/images`);
        const imagesData = await imagesResponse.json();
        setScreensaverImages(imagesData.images || []);
      } catch (error) {
        console.error('Failed to load screensaver config:', error);
      }
    };
    loadScreensaverConfig();
  }, [serverAddress]);

  // Countdown logging for screensaver
  useEffect(() => {
    const logCountdown = () => {
      if (screensaverActive) {
        return; // Don't log when screensaver is active
      }
      
      const timeSinceActivity = Date.now() - lastActivityTime.current;
      const timeoutMs = screensaverTimeout * 60 * 1000;
      const timeRemaining = timeoutMs - timeSinceActivity;
      
      if (timeRemaining > 0) {
        const minutes = Math.floor(timeRemaining / 60000);
        const seconds = Math.floor((timeRemaining % 60000) / 1000);
        console.log(`[Screensaver] Time remaining: ${minutes}m ${seconds}s`);
      } else {
        console.log(`[Screensaver] Screensaver should activate now`);
      }
    };

    // Log countdown every 5 seconds
    countdownTimer.current = setInterval(logCountdown, 5000);
    
    return () => {
      if (countdownTimer.current) {
        clearInterval(countdownTimer.current);
      }
    };
  }, [screensaverActive, screensaverTimeout]);

  // Inactivity detection
  useEffect(() => {
    const timeoutMs = screensaverTimeout * 60 * 1000;
    
    const handleActivity = () => {
      lastActivityTime.current = Date.now();
      if (screensaverActive) {
        setScreensaverActive(false);
      }
      // Reset inactivity timer
      if (inactivityTimer.current) {
        clearTimeout(inactivityTimer.current);
      }
      // Set new timer
      inactivityTimer.current = setTimeout(() => {
        setScreensaverActive(true);
      }, timeoutMs);
    };

    // Track various user interactions (but throttle mousemove to avoid too many calls)
    let mousemoveThrottle = null;
    const handleMouseMove = () => {
      if (mousemoveThrottle) return;
      mousemoveThrottle = setTimeout(() => {
        handleActivity();
        mousemoveThrottle = null;
      }, 1000); // Throttle mousemove to once per second
    };

    const events = ['mousedown', 'keypress', 'scroll', 'touchstart', 'click', 'wheel'];
    events.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });
    
    // Special handling for mousemove
    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // Initial timer
    inactivityTimer.current = setTimeout(() => {
      setScreensaverActive(true);
    }, timeoutMs);

    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      window.removeEventListener('mousemove', handleMouseMove);
      if (inactivityTimer.current) {
        clearTimeout(inactivityTimer.current);
      }
      if (mousemoveThrottle) {
        clearTimeout(mousemoveThrottle);
      }
    };
  }, [screensaverActive, screensaverTimeout]);

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
      // Reset inactivity timer on user action
      lastActivityTime.current = Date.now();
      if (screensaverActive) {
        setScreensaverActive(false);
      }
      // Clear and reset timer
      if (inactivityTimer.current) {
        clearTimeout(inactivityTimer.current);
      }
      const timeoutMs = screensaverTimeout * 60 * 1000;
      inactivityTimer.current = setTimeout(() => {
        setScreensaverActive(true);
      }, timeoutMs);
      
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

  const handleScreensaverInteraction = () => {
    setScreensaverActive(false);
    lastActivityTime.current = Date.now();
    // Reset timer
    if (inactivityTimer.current) {
      clearTimeout(inactivityTimer.current);
    }
    const timeoutMs = screensaverTimeout * 60 * 1000;
    inactivityTimer.current = setTimeout(() => {
      setScreensaverActive(true);
    }, timeoutMs);
  };

  const handleTabChange = (tabIndex) => {
    setSelectedTab(tabIndex);
    // Reset inactivity on tab change
    lastActivityTime.current = Date.now();
    if (screensaverActive) {
      setScreensaverActive(false);
    }
    if (inactivityTimer.current) {
      clearTimeout(inactivityTimer.current);
    }
    const timeoutMs = screensaverTimeout * 60 * 1000;
    inactivityTimer.current = setTimeout(() => {
      setScreensaverActive(true);
    }, timeoutMs);
  };

  const handleServerAddressChange = (e) => {
    if (e.key === 'Enter') {
      setServerAddress(e.target.value);
      // Reset inactivity on server address change
      lastActivityTime.current = Date.now();
      if (screensaverActive) {
        setScreensaverActive(false);
      }
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
      {screensaverActive && (
        <Screensaver
          images={screensaverImages}
          onInteraction={handleScreensaverInteraction}
        />
      )}
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
          onClick={() => handleTabChange(0)}
        >
          💬 Chat
        </button>
        <button
          className={`nav-button ${selectedTab === 1 ? 'active' : ''}`}
          onClick={() => handleTabChange(1)}
        >
          🏠 Devices
        </button>
        <button
          className={`nav-button ${selectedTab === 2 ? 'active' : ''}`}
          onClick={() => handleTabChange(2)}
        >
          🤖 Robot
        </button>
      </div>
    </div>
  );
}

export default App;

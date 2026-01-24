import React, { useState, useEffect } from 'react';
import './Screensaver.css';

function Screensaver({ serverAddress, onInteraction }) {
  const [currentImageUrl, setCurrentImageUrl] = useState(null);
  const [hasImages, setHasImages] = useState(true);

  const loadRandomImage = async () => {
    try {
      const response = await fetch(`http://${serverAddress}/api/screensaver/random-image`);
      const data = await response.json();
      if (data.imageUrl) {
        // Construct full URL with cache busting to ensure new image loads
        const fullUrl = `http://${serverAddress}${data.imageUrl}?t=${Date.now()}`;
        setCurrentImageUrl(fullUrl);
        setHasImages(true);
      } else {
        setHasImages(false);
      }
    } catch (error) {
      console.error('Failed to load screensaver image:', error);
      setHasImages(false);
    }
  };

  useEffect(() => {
    // Load initial image
    loadRandomImage();

    // Change image every 30 seconds
    const interval = setInterval(() => {
      loadRandomImage();
    }, 30000);

    return () => clearInterval(interval);
  }, [serverAddress]);

  // Handle any user interaction to exit screensaver
  const handleInteraction = (e) => {
    e.preventDefault();
    onInteraction();
  };

  if (!hasImages || !currentImageUrl) {
    return (
      <div className="screensaver" onClick={handleInteraction}>
        <div className="screensaver-placeholder">
          <p>No images found in screensaver folder</p>
          <p>Click anywhere to exit</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="screensaver"
      onClick={handleInteraction}
      onKeyDown={handleInteraction}
      onMouseMove={handleInteraction}
      onTouchStart={handleInteraction}
      tabIndex={0}
    >
      <img
        src={currentImageUrl}
        alt="Screensaver"
        className="screensaver-image"
        onError={(e) => {
          // If image fails to load, try to load another one
          console.error('Failed to load screensaver image, trying another...');
          loadRandomImage();
        }}
      />
    </div>
  );
}

export default Screensaver;

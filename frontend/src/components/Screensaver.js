import React, { useState, useEffect } from 'react';
import './Screensaver.css';

function Screensaver({ images, onInteraction }) {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [imageUrls, setImageUrls] = useState([]);

  useEffect(() => {
    // Load images
    const loadImages = async () => {
      const urls = images.map((img) => `/api/screensaver/image/${encodeURIComponent(img)}`);
      setImageUrls(urls);
      // Shuffle images for random order
      const shuffled = [...urls].sort(() => Math.random() - 0.5);
      setImageUrls(shuffled);
    };

    if (images && images.length > 0) {
      loadImages();
    }
  }, [images]);

  useEffect(() => {
    if (imageUrls.length === 0) return;

    // Change image every 30 seconds
    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % imageUrls.length);
    }, 30000);

    return () => clearInterval(interval);
  }, [imageUrls]);

  // Handle any user interaction to exit screensaver
  const handleInteraction = (e) => {
    e.preventDefault();
    onInteraction();
  };

  if (imageUrls.length === 0) {
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
        src={imageUrls[currentImageIndex]}
        alt={`Screensaver ${currentImageIndex + 1}`}
        className="screensaver-image"
        onError={(e) => {
          // If image fails to load, skip to next
          setCurrentImageIndex((prev) => (prev + 1) % imageUrls.length);
        }}
      />
    </div>
  );
}

export default Screensaver;

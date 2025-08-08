import React from 'react';

const ErrorMessage = ({ message, onClose }) => {
  return (
    <div className="error-message-container">
      <div className="error-content">
        <span className="error-text">{message}</span>
        <button onClick={onClose} className="error-close">
          ×
        </button>
      </div>
    </div>
  );
};

export default ErrorMessage;
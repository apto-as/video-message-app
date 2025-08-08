import React from 'react';

const TextInput = ({ value, onChange }) => {
  const handleChange = (e) => {
    const newValue = e.target.value;
    if (newValue.length <= 100) {
      onChange(newValue);
    }
  };

  return (
    <div className="text-input-container">
      <label htmlFor="message-text">メッセージ</label>
      <textarea
        id="message-text"
        value={value}
        onChange={handleChange}
        placeholder="お誕生日おめでとう！素敵な一年になりますように。"
        className="text-input"
        rows={3}
      />
      <div className="character-count">
        {value.length}/100文字
      </div>
    </div>
  );
};

export default TextInput;
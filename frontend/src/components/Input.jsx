import React, { useState, forwardRef } from 'react';

const Input = forwardRef(({ onSendMessage, disabled }, ref) => {
    const [text, setText] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (text.trim() && !disabled) {
            onSendMessage(text);
            setText('');
        }
    };

    return (
        <form onSubmit={handleSubmit} className="flex items-center p-4">
            <input
                ref={ref}
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Type your message..."
                className="flex-grow p-2 rounded-l-lg bg-neutral-700 text-neutral-100 focus:outline-none"
                disabled={disabled}
            />
            <button type="submit" className="bg-blue-600 text-white p-2 rounded-r-lg disabled:bg-neutral-600" disabled={disabled}>
                Send
            </button>
        </form>
    );
});

export default Input;

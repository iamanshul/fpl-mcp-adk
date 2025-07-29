import React from 'react';

const Chat = ({ messages }) => {
    return (
        <div className="chat-messages space-y-4">
            {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`p-4 rounded-lg max-w-3xl ${msg.sender === 'user' ? 'bg-blue-600 text-white' : 'bg-neutral-700 text-neutral-100'}`}>
                        {msg.text}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default Chat;
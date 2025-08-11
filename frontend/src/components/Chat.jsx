import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import LoadingSpinner from './LoadingSpinner.jsx';

const Chat = ({ messages, isLoading }) => {
    const chatEndRef = useRef(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="chat-messages space-y-4">
            {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`p-4 rounded-lg max-w-3xl ${msg.sender === 'user' ? 'bg-blue-600 text-white' : 'bg-neutral-700 text-neutral-100'}`}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                    </div>
                </div>
            ))}
            {isLoading && <LoadingSpinner />}
            <div ref={chatEndRef} />
        </div>
    );
};

export default Chat;

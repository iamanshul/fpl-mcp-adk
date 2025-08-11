import React, { useState, useEffect, useRef } from 'react';
import Chat from './components/Chat.jsx';
import Input from './components/Input.jsx';
import { createSession, postMessage } from './services/api.js';
import logo from './assets/FPL_logo.png';

const App = () => {
    const [messages, setMessages] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [userId, setUserId] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const chatEndRef = useRef(null);
    const inputRef = useRef(null);

    // Effect for auto-scrolling
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Effect for focusing input
    useEffect(() => {
        if (!isLoading) {
            inputRef.current?.focus();
        }
    }, [isLoading]);

    useEffect(() => {
        const initSession = async () => {
            const newUserId = `webapp-user-${Date.now()}`;
            setUserId(newUserId);
            try {
                const session = await createSession(newUserId);
                setSessionId(session.session_id);
                // Ask the agent for a joke to start the session
                const data = await postMessage(newUserId, session.session_id, "Tell me a one-line football (soccer) joke.");
                setMessages([{ sender: 'agent', text: data.response }]);
            } catch (error) {
                console.error("Initialization Failed:", error);
                setMessages([{ sender: 'agent', text: 'Error: Could not connect to the agent backend. Please ensure the backend server is running.' }]);
            }
        };
        initSession();
    }, []);

    const handleSendMessage = async (messageText) => {
        if (!sessionId || !userId || isLoading) return;

        setIsLoading(true);
        const newMessages = [...messages, { sender: 'user', text: messageText }];
        setMessages(newMessages);

        try {
            const data = await postMessage(userId, sessionId, messageText);
            setMessages(prev => [...prev, { sender: 'agent', text: data.response }]);
        } catch (error) {
            console.error("handleSendMessage Failed:", error);
            setMessages(prev => [...prev, { sender: 'agent', text: 'Sorry, I encountered an error. Please check the console for details.' }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-neutral-800 text-neutral-100 font-sans antialiased">
            <header className="flex justify-center p-4 w-full max-w-4xl mx-auto">
                <img src={logo} alt="FPL Logo" className="w-2/5" />
            </header>
            <main className="flex-1 flex flex-col items-center overflow-hidden w-full">
                <div className={`w-full max-w-4xl flex-1 flex flex-col overflow-y-auto p-4 border border-neutral-700 rounded-lg shadow-lg bg-neutral-900 ${messages.length <= 1 ? 'justify-center' : ''}`}>
                    <div className="chat-container flex-1">
                        <Chat messages={messages} isLoading={isLoading} />
                        <div ref={chatEndRef} />
                    </div>
                    <Input ref={inputRef} onSendMessage={handleSendMessage} disabled={isLoading} />
                </div>
            </main>
        </div>
    );
};

export default App;

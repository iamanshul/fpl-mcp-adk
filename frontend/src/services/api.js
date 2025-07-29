// frontend/src/services/api.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";

export const createSession = async (userId) => {
    const response = await fetch(`${API_BASE_URL}/create_session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
    });
    if (!response.ok) {
        // Log the error for debugging
        const err = await response.json();
        console.error("API Error (createSession):", err);
        throw new Error('Failed to create session');
    }
    return response.json();
};

export const postMessage = async (userId, sessionId, message) => {
    const response = await fetch(`${API_BASE_URL}/post_message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, session_id: sessionId, message: message }),
    });
    if (!response.ok) {
        // Log the error for debugging
        const err = await response.json();
        console.error("API Error (postMessage):", err);
        throw new Error('Failed to send message');
    }
    return response.json();
};
import "./Chatbot.css";
import { useState } from "react";

export default function Chatbot() {
    const [messages, setMessages] = useState([
        {
            role: "assistant",
            content: "Hi! How can I help you?",
        },
    ]);

    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!input.trim() || loading) {
            return;
        }

        const userMessage = {
            role: "user",
            content: input.trim(),
        };

        const updatedMessages = [...messages, userMessage];

        setMessages(updatedMessages);
        setInput("");
        setLoading(true);

        try {
            const response = await fetch(
                "http://127.0.0.1:8000/api/chat",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        messages: updatedMessages,
                    }),
                }
            );

            if (!response.ok) {
                throw new Error("Failed to get response");
            }

            const data = await response.json();

            setMessages([
                ...updatedMessages,
                {
                    role: "assistant",
                    content: data.message,
                },
            ]);
        } catch (error) {
            console.error(error);

            setMessages([
                ...updatedMessages,
                {
                    role: "assistant",
                    content:
                        "Sorry, something went wrong while contacting the AI.",
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="chatbot">
            <div className="chatbot-header">
                <h2>AI Assistant</h2>
                <span>Powered by Groq</span>
            </div>

            <div className="chatbot-messages">
                {messages.map((message, index) => (
                    <div
                        key={index}
                        className={`message ${message.role}`}
                    >
                        <div className="message-bubble">
                            {message.content}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="message assistant">
                        <div className="message-bubble">
                            Thinking...
                        </div>
                    </div>
                )}
            </div>

            <div className="chatbot-input">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask me anything..."
                    rows={1}
                    disabled={loading}
                />

                <button
                    onClick={sendMessage}
                    disabled={!input.trim() || loading}
                >
                    Send
                </button>
            </div>
        </div>
    );
}
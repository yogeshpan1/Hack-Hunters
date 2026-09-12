import "./Chatbot.css";
import { useState } from "react";

const API_URL = import.meta?.env?.VITE_API_URL || "http://127.0.0.1:8000";

export default function Chatbot() {
    const [messages, setMessages] = useState([{ role: "assistant", content: "I see you are reviewing your academic operations. How can I help?" }]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [view, setView] = useState("assistant");
    const [email, setEmail] = useState({ to: "", subject: "", message: "" });
    const [emailStatus, setEmailStatus] = useState("");
    const [sendingEmail, setSendingEmail] = useState(false);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;
        const userMessage = { role: "user", content: input.trim() };
        const updatedMessages = [...messages, userMessage];
        setMessages(updatedMessages); setInput(""); setLoading(true);
        try {
            const response = await fetch(`${API_URL}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages: updatedMessages }) });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Failed to get response");
            setMessages([...updatedMessages, { role: "assistant", content: data.message }]);
        } catch (error) {
            console.error(error);
            setMessages([...updatedMessages, { role: "assistant", content: "Sorry, something went wrong while contacting Nexus AI." }]);
        } finally { setLoading(false); }
    };

    const sendEmail = async (event) => {
        event.preventDefault();
        if (!email.to.trim() || !email.subject.trim() || !email.message.trim() || sendingEmail) return;
        setSendingEmail(true); setEmailStatus("");
        try {
            const response = await fetch(`${API_URL}/api/email`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(email) });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Unable to send email.");
            setEmailStatus("Email sent successfully."); setEmail({ to: "", subject: "", message: "" });
        } catch (error) { setEmailStatus(error.message || "Unable to send email."); }
        finally { setSendingEmail(false); }
    };

    const handleKeyDown = (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } };

    return <aside className="chatbot" aria-label="Nexus AI side panel">
        <div className="chatbot-header"><div className="nexus-title"><span className="sparkle">✦</span><h2>NEXUS AI</h2></div><span className="close-icon" aria-hidden="true">×</span></div>
        <div className="context-row"><span>▣</span><div><strong>Context Active:</strong><small>Academic operations</small></div></div>
        <div className="panel-tabs" role="tablist"><button className={view === "assistant" ? "active" : ""} onClick={() => setView("assistant")}>Assistant</button><button className={view === "email" ? "active" : ""} onClick={() => setView("email")}>Send email</button></div>
        {view === "assistant" ? <>
            <div className="chatbot-messages">{messages.map((message, index) => <div key={index} className={`message ${message.role}`}><div className="message-bubble">{message.content}</div></div>)}{loading && <div className="message assistant"><div className="message-bubble">Nexus AI is thinking...</div></div>}</div>
            <div className="chatbot-input"><textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="Ask NEXUS..." rows={1} disabled={loading} /><button onClick={sendMessage} disabled={!input.trim() || loading}><span aria-hidden="true">➤</span><span className="sr-only">Send</span></button></div>
        </> : <form className="email-form" onSubmit={sendEmail}>
            <p>Send an operational update securely through Resend.</p>
            <label>To<input type="email" value={email.to} onChange={(e) => setEmail({ ...email, to: e.target.value })} placeholder="staff@example.com" required /></label>
            <label>Subject<input value={email.subject} onChange={(e) => setEmail({ ...email, subject: e.target.value })} placeholder="Schedule update" required /></label>
            <label>Message<textarea value={email.message} onChange={(e) => setEmail({ ...email, message: e.target.value })} placeholder="Write your message..." rows={7} required /></label>
            {emailStatus && <p className={`email-status ${emailStatus.includes("success") ? "success" : "error"}`}>{emailStatus}</p>}
            <button className="email-send" type="submit" disabled={sendingEmail}>{sendingEmail ? "Sending..." : "Send email"}</button>
        </form>}
    </aside>;
}

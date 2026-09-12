import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

function ClassAllocation() {
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [allocating, setAllocating] = useState(false);
  const [sending, setSending] = useState(false);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [sendSummary, setSendSummary] = useState(null);

  const [expanded, setExpanded] = useState({});
  const [testEmail, setTestEmail] = useState("");
  const [testStatus, setTestStatus] = useState("");

  async function loadClasses() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(`${API}/classes`);

      if (!response.ok) {
        throw new Error("Failed to load classes");
      }

      const data = await response.json();
      setClasses(data.classes || []);
    } catch (err) {
      console.error("CLASSES ERROR:", err);
      setError("Could not load class allocation from the backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadClasses();
  }, []);

  async function handleAllocate() {
    try {
      setAllocating(true);
      setError("");
      setNotice(null);
      setSendSummary(null);

      const response = await fetch(`${API}/allocate-classes`, {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to allocate classes");
      }

      setClasses(data.classes || []);
      setNotice(`✓ ${data.message}`);
    } catch (err) {
      console.error("ALLOCATE ERROR:", err);
      setError(err.message || "Could not allocate classes.");
    } finally {
      setAllocating(false);
    }
  }

  async function handleSendEmails() {
    try {
      setSending(true);
      setError("");
      setSendSummary(null);

      const response = await fetch(`${API}/send-emails`, {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to send emails");
      }

      setSendSummary(data);
      await loadClasses();
    } catch (err) {
      console.error("SEND EMAILS ERROR:", err);
      setError(err.message || "Could not send emails.");
    } finally {
      setSending(false);
    }
  }

  async function handleSendTestEmail() {
    if (!testEmail) return;

    try {
      setTestStatus("Sending...");

      const response = await fetch(`${API}/send-test-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: testEmail }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to send test email");
      }

      setTestStatus(`✓ Sent to ${testEmail}`);
    } catch (err) {
      setTestStatus(`✗ ${err.message}`);
    }
  }

  function toggleExpand(allocationId) {
    setExpanded((prev) => ({
      ...prev,
      [allocationId]: !prev[allocationId],
    }));
  }

  const totalStudents = classes.reduce(
    (sum, c) => sum + (c.student_count || 0),
    0
  );

  const totalEmailed = classes.reduce(
    (sum, c) =>
      sum + (c.students || []).filter((s) => s.email_sent).length,
    0
  );

  return (
    <div className="allocation-section">
      <h2>Class Allocation</h2>
      <p className="allocation-subtitle">
        Split students into 7 classes using the <strong>Skill</strong> block
        rooms, then notify everyone by email.
      </p>

      <div className="allocation-toolbar">
        <button
          className="check-button"
          onClick={handleAllocate}
          disabled={allocating}
        >
          {allocating ? "Allocating..." : "🎲 Generate Allocation"}
        </button>

        <button
          className="check-button send-button"
          onClick={handleSendEmails}
          disabled={sending || classes.length === 0}
        >
          {sending ? "Sending..." : "✉️ Send Emails to All"}
        </button>
      </div>

      {error && <div className="error-message">❌ {error}</div>}
      {notice && <div className="success-message">{notice}</div>}

      {sendSummary && (
        <div
          className={
            sendSummary.failed > 0 ? "warning-message" : "success-message"
          }
        >
          ✉️ Sent {sendSummary.sent} / {sendSummary.total} emails
          {sendSummary.failed > 0
            ? ` — ${sendSummary.failed} failed (check addresses / Resend domain verification).`
            : "."}
        </div>
      )}

      {classes.length > 0 && (
        <div className="allocation-stats">
          <div className="stat-pill">
            <span className="stat-number">{classes.length}</span>
            <span className="stat-label">Classes</span>
          </div>
          <div className="stat-pill">
            <span className="stat-number">{totalStudents}</span>
            <span className="stat-label">Students</span>
          </div>
          <div className="stat-pill">
            <span className="stat-number">{totalEmailed}</span>
            <span className="stat-label">Emailed</span>
          </div>
        </div>
      )}

      {loading ? (
        <p>Loading class allocation...</p>
      ) : classes.length === 0 ? (
        <div className="error-message">
          No classes allocated yet. Click "Generate Allocation" to split
          students into 7 Skill-block classes.
        </div>
      ) : (
        <div className="class-grid">
          {classes.map((classInfo) => {
            const fillPct = Math.min(
              100,
              Math.round(
                (classInfo.student_count / classInfo.room_capacity) * 100
              )
            );
            const emailedCount = (classInfo.students || []).filter(
              (s) => s.email_sent
            ).length;

            return (
              <div className="class-card" key={classInfo.allocation_id}>
                <div className="class-card-header">
                  <h3>{classInfo.class_name}</h3>
                  <span className="block-badge">{classInfo.block_name}</span>
                </div>

                <p className="room-line">
                  {classInfo.room_name}{" "}
                  <span className="room-code">
                    ({classInfo.room_code})
                  </span>
                </p>

                <div className="capacity-bar-track">
                  <div
                    className="capacity-bar-fill"
                    style={{ width: `${fillPct}%` }}
                  />
                </div>
                <p className="capacity-line">
                  {classInfo.student_count} / {classInfo.room_capacity}{" "}
                  students &middot; {emailedCount} emailed
                </p>

                <button
                  className="expand-button"
                  onClick={() => toggleExpand(classInfo.allocation_id)}
                >
                  {expanded[classInfo.allocation_id]
                    ? "Hide students ▲"
                    : "Show students ▼"}
                </button>

                {expanded[classInfo.allocation_id] && (
                  <ul className="student-list">
                    {classInfo.students.map((student) => (
                      <li key={student.student_id}>
                        <span className="student-name">
                          {student.first_name} {student.last_name}
                        </span>
                        <span className="student-email">
                          {student.email}
                        </span>
                        <span
                          className={
                            student.email_sent
                              ? "sent-badge sent"
                              : "sent-badge"
                          }
                        >
                          {student.email_sent ? "✓ sent" : "not sent"}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="test-email-box">
        <h3>Send a test email</h3>
        <p className="allocation-subtitle">
          Try the Resend integration with any address before emailing the
          whole cohort.
        </p>
        <div className="test-email-row">
          <input
            type="email"
            placeholder="you@example.com"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
          />
          <button className="check-button" onClick={handleSendTestEmail}>
            Send Test
          </button>
        </div>
        {testStatus && <p className="test-status">{testStatus}</p>}
      </div>
    </div>
  );
}

export default ClassAllocation;

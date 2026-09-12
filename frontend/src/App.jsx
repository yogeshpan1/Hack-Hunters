import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [clashes, setClashes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function checkClashes() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/check-clashes`);

      if (!response.ok) {
        throw new Error("Failed to check clashes");
      }

      const data = await response.json();

      console.log("CLASH DATA:", data);

      setClashes(data.clashes || []);
    } catch (err) {
      console.error(err);
      setError("Could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    checkClashes();
  }, []);

  return (
    <div className="app">
      <div className="container">

        <h1>Academic Timetable</h1>

        <p className="subtitle">
          Timetable Clash Detection System
        </p>

        <button
          className="check-button"
          onClick={checkClashes}
          disabled={loading}
        >
          {loading ? "Checking..." : "Check Clashes"}
        </button>

        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        {!loading && !error && clashes.length === 0 && (
          <div className="success-message">
            ✓ No clashes detected
          </div>
        )}

        {!loading && clashes.length > 0 && (
          <div className="clash-list">

            <h2>
              ⚠️ {clashes.length} Clash
              {clashes.length !== 1 ? "es" : ""} Detected
            </h2>

            {clashes.map((clash, index) => (
              <div className="clash-card" key={index}>

                <h3>
                  Clash {index + 1}
                </h3>

                <div className="clash-type">
                  {clash.type
                    ? clash.type.replaceAll("_", " ")
                    : "TIMETABLE CLASH"}
                </div>

                <p className="message">
                  {typeof clash.message === "string"
                    ? clash.message
                    : "Two timetable entries conflict."}
                </p>

                {clash.entry1 && (
                  <div className="class-info">
                    <strong>Class 1</strong>

                    <p>
                      Course:{" "}
                      {clash.entry1.course_code ||
                        clash.entry1.course ||
                        "Unknown"}
                    </p>

                    <p>
                      Room:{" "}
                      {clash.entry1.room || "Unknown"}
                    </p>

                    <p>
                      Day:{" "}
                      {clash.entry1.day || "Unknown"}
                    </p>

                    <p>
                      Time:{" "}
                      {clash.entry1.start || ""}
                      {" - "}
                      {clash.entry1.end || ""}
                    </p>
                  </div>
                )}

                {clash.entry2 && (
                  <div className="class-info">
                    <strong>Class 2</strong>

                    <p>
                      Course:{" "}
                      {clash.entry2.course_code ||
                        clash.entry2.course ||
                        "Unknown"}
                    </p>

                    <p>
                      Room:{" "}
                      {clash.entry2.room || "Unknown"}
                    </p>

                    <p>
                      Day:{" "}
                      {clash.entry2.day || "Unknown"}
                    </p>

                    <p>
                      Time:{" "}
                      {clash.entry2.start || ""}
                      {" - "}
                      {clash.entry2.end || ""}
                    </p>
                  </div>
                )}

              </div>
            ))}

          </div>
        )}

      </div>
    </div>
  );
}

export default App;
import { useEffect, useState } from "react";
import "./App.css";
import Chatbot from "../component/Chatbot";

const API = "http://127.0.0.1:8000";

const days = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
];

function App() {
  const [sessions, setSessions] = useState([]);
  const [clashes, setClashes] = useState([]);

  const [loadingTimetable, setLoadingTimetable] = useState(true);
  const [loadingClashes, setLoadingClashes] = useState(false);

  const [error, setError] = useState("");

  // =========================================
  // LOAD TIMETABLE FROM DATABASE
  // =========================================

  async function loadTimetable() {
    try {
      setLoadingTimetable(true);
      setError("");

      const response = await fetch(`${API}/timetable`);

      if (!response.ok) {
        throw new Error("Failed to load timetable");
      }

      const data = await response.json();

      console.log("TIMETABLE FROM DATABASE:");
      console.log(data);

      setSessions(Array.isArray(data) ? data : []);

    } catch (err) {
      console.error("TIMETABLE ERROR:", err);
      setError("Could not load timetable from the backend.");
    } finally {
      setLoadingTimetable(false);
    }
  }

  // =========================================
  // CHECK CLASHES
  // =========================================

  async function checkClashes() {
    try {
      setLoadingClashes(true);

      const response = await fetch(`${API}/check-clashes`);

      if (!response.ok) {
        throw new Error("Failed to check clashes");
      }

      const data = await response.json();

      console.log("CLASH DATA:");
      console.log(data);

      setClashes(data.clashes || []);

    } catch (err) {
      console.error("CLASH ERROR:", err);
      setError("Could not connect to the backend.");
    } finally {
      setLoadingClashes(false);
    }
  }

  // =========================================
  // LOAD DATA WHEN APP STARTS
  // =========================================

  useEffect(() => {
    loadTimetable();
    checkClashes();
  }, []);

  // =========================================
  // GET UNIQUE TIME SLOTS FROM DATABASE
  // =========================================

  const timeSlots = [
    ...new Set(
      sessions
        .map((session) => {
          if (!session.start_time || !session.end_time) {
            return null;
          }

          return `${session.start_time} - ${session.end_time}`;
        })
        .filter(Boolean)
    ),
  ];

  // =========================================
  // GET SESSIONS FOR A DAY AND TIME
  // =========================================

  function getSessions(day, timeSlot) {
    const [startTime, endTime] = timeSlot.split(" - ");

    return sessions.filter((session) => {

      const sessionDay = String(
        session.day_of_week || ""
      ).trim();

      const sessionStart = String(
        session.start_time || ""
      ).trim();

      const sessionEnd = String(
        session.end_time || ""
      ).trim();

      return (
        sessionDay === day &&
        sessionStart === startTime &&
        sessionEnd === endTime
      );
    });
  }

  // =========================================
  // FRONTEND
  // =========================================

  return (
    <div className="app">

      <div className="container">

        <h1>
          Academic Timetable
        </h1>

        <p className="subtitle">
          Timetable Clash Detection System
        </p>

        {/* ================================= */}
        {/* TIMETABLE */}
        {/* ================================= */}

        <h2>
          Weekly Timetable
        </h2>

        {loadingTimetable ? (

          <p>
            Loading timetable from database...
          </p>

        ) : error ? (

          <div className="error-message">
            ❌ {error}
          </div>

        ) : sessions.length === 0 ? (

          <div className="error-message">
            No timetable sessions were found in the database.
          </div>

        ) : (

          <table className="timetable">

            <thead>

              <tr>

                <th>
                  Time
                </th>

                {days.map((day) => (

                  <th key={day}>
                    {day}
                  </th>

                ))}

              </tr>

            </thead>

            <tbody>

              {timeSlots.map((timeSlot) => (

                <tr key={timeSlot}>

                  <td className="time">
                    {timeSlot}
                  </td>

                  {days.map((day) => {

                    const daySessions =
                      getSessions(
                        day,
                        timeSlot
                      );

                    return (

                      <td key={day}>

                        {daySessions.length > 0 ? (

                          daySessions.map(
                            (session, index) => (

                              <div
                                className="session"
                                key={
                                  session.session_id ||
                                  `${day}-${timeSlot}-${index}`
                                }
                              >

                                <strong>
                                  {session.module_code}
                                </strong>

                                <p>
                                  {session.module_name}
                                </p>

                                <small>
                                  Faculty:{" "}
                                  {session.faculty_name}
                                </small>

                                <small>
                                  Room:{" "}
                                  {session.room_name}
                                </small>

                                <small>
                                  Cohort:{" "}
                                  {session.cohort_name}
                                </small>

                                <small>
                                  {session.session_type}
                                </small>

                              </div>

                            )
                          )

                        ) : (

                          <span className="empty">
                            —
                          </span>

                        )}

                      </td>

                    );

                  })}

                </tr>

              ))}

            </tbody>

          </table>

        )}

        {/* ================================= */}
        {/* CLASH DETECTION */}
        {/* ================================= */}

        <div className="clash-section">

          <h2>
            Clash Detection
          </h2>

          <button
            className="check-button"
            onClick={checkClashes}
            disabled={loadingClashes}
          >

            {loadingClashes
              ? "Checking..."
              : "Check Clashes"}

          </button>

          {/* NO CLASHES */}

          {!loadingClashes &&
            clashes.length === 0 && (
              <div className="success-message">
                ✓ No clashes detected
              </div>
            )}

          {/* CLASHES */}

          {!loadingClashes &&
            clashes.length > 0 && (

              <div className="clash-list">

                <h2>
                  ⚠️ {clashes.length} Clash
                  {clashes.length !== 1
                    ? "es"
                    : ""}{" "}
                  Detected
                </h2>

                {clashes.map(
                  (clash, index) => (

                    <div
                      className="clash-card"
                      key={index}
                    >

                      <h3>
                        Clash {index + 1}
                      </h3>

                      <div className="clash-type">
                        {clash.type
                          ? clash.type.replaceAll(
                              "_",
                              " "
                            )
                          : "TIMETABLE CLASH"}
                      </div>

                      <p className="message">
                        {clash.message ||
                          "Two timetable entries conflict."}
                      </p>

                      <p>
                        Session 1 ID:{" "}
                        {clash.session1 || "Unknown"}
                      </p>

                      <p>
                        Session 2 ID:{" "}
                        {clash.session2 || "Unknown"}
                      </p>

                    </div>

                  )
                )}

              </div>

            )}

            <div>
               <Chatbot />
            </div>
        </div>

      </div>

    </div>
  );
}

export default App;
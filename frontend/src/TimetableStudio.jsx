import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000";

const DAYS = [
  { key: "Monday", letter: "M" },
  { key: "Tuesday", letter: "T" },
  { key: "Wednesday", letter: "W" },
  { key: "Thursday", letter: "T" },
  { key: "Friday", letter: "F" },
];

const DAY_START_MIN = 8 * 60; // 08:00
const DAY_END_MIN = 17 * 60; // 17:00
const DAY_SPAN_MIN = DAY_END_MIN - DAY_START_MIN;
const HOUR_MARKS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17];

function toMinutes(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function timesOverlap(a, b) {
  return a.day_of_week === b.day_of_week && a.start_time < b.end_time && b.start_time < a.end_time;
}

// Lays overlapping sessions out side-by-side within a lane (like a calendar
// day view), instead of stacking them illegibly on top of each other - this
// is exactly what a genuine ROOM/FACULTY/COHORT clash looks like.
function layoutOverlaps(laneSessions) {
  const sorted = [...laneSessions].sort(
    (a, b) => toMinutes(a.start_time) - toMinutes(b.start_time)
  );

  const columnEnds = [];
  const placed = sorted.map((session) => {
    const start = toMinutes(session.start_time);
    const end = toMinutes(session.end_time);

    let col = columnEnds.findIndex((endMin) => endMin <= start);
    if (col === -1) {
      col = columnEnds.length;
      columnEnds.push(end);
    } else {
      columnEnds[col] = end;
    }

    return { session, col, start, end };
  });

  return placed.map((p) => {
    let totalCols = p.col + 1;
    for (const q of placed) {
      if (p.start < q.end && q.start < p.end) {
        totalCols = Math.max(totalCols, q.col + 1);
      }
    }
    return { session: p.session, col: p.col, totalCols };
  });
}

function TimetableStudio({ searchTerm = "" }) {
  const [rooms, setRooms] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [clashes, setClashes] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedDay, setSelectedDay] = useState("Monday");
  const [groupBy, setGroupBy] = useState("room"); // room | cohort | faculty | module
  const [blockFilter, setBlockFilter] = useState("All");
  const [showAllRooms, setShowAllRooms] = useState(false);
  const [showUtilization, setShowUtilization] = useState(true);
  const [conflictsOnly, setConflictsOnly] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState(null);

  const [resolving, setResolving] = useState(false);
  const [resolveNotice, setResolveNotice] = useState("");

  async function loadAll() {
    try {
      setLoading(true);
      setError("");

      const [roomsRes, timetableRes, clashesRes] = await Promise.all([
        fetch(`${API}/rooms`),
        fetch(`${API}/timetable`),
        fetch(`${API}/check-clashes`),
      ]);

      if (!roomsRes.ok || !timetableRes.ok || !clashesRes.ok) {
        throw new Error("Failed to load timetable data");
      }

      const roomsData = await roomsRes.json();
      const timetableData = await timetableRes.json();
      const clashesData = await clashesRes.json();

      setRooms(roomsData.rooms || []);
      setSessions(Array.isArray(timetableData) ? timetableData : []);
      setClashes(clashesData.clashes || []);
    } catch (err) {
      console.error("TIMETABLE STUDIO ERROR:", err);
      setError("Could not load the timetable from the backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  // =========================================
  // CONFLICT / WARNING LOOKUP
  // =========================================

  const { conflictMap, warningMap } = useMemo(() => {
    const conflicts = new Map();
    const warnings = new Map();

    for (const clash of clashes) {
      if (clash.type === "CAPACITY_CLASH") {
        const list = warnings.get(clash.session) || [];
        list.push(clash);
        warnings.set(clash.session, list);
      } else {
        for (const sid of [clash.session1, clash.session2]) {
          const list = conflicts.get(sid) || [];
          list.push(clash);
          conflicts.set(sid, list);
        }
      }
    }

    return { conflictMap: conflicts, warningMap: warnings };
  }, [clashes]);

  const blockNames = useMemo(() => {
    const set = new Set(rooms.map((r) => r.block_name).filter(Boolean));
    return ["All", ...Array.from(set).sort()];
  }, [rooms]);

  const daySessions = useMemo(
    () => sessions.filter((s) => s.day_of_week === selectedDay),
    [sessions, selectedDay]
  );

  const toResolveCount = useMemo(() => {
    const ids = new Set();
    for (const s of daySessions) {
      if (conflictMap.has(s.session_id) || warningMap.has(s.session_id)) {
        ids.add(s.session_id);
      }
    }
    return ids.size;
  }, [daySessions, conflictMap, warningMap]);

  // =========================================
  // LANES (columns)
  // =========================================

  const lanes = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    const hasIssue = (s) => conflictMap.has(s.session_id) || warningMap.has(s.session_id);

    let built;

    if (groupBy === "room") {
      const roomsWithSessions = new Set(daySessions.map((s) => s.room_id));

      let candidateRooms = rooms;
      if (blockFilter !== "All") {
        candidateRooms = candidateRooms.filter((r) => r.block_name === blockFilter);
      }
      if (!showAllRooms) {
        candidateRooms = candidateRooms.filter((r) => roomsWithSessions.has(r.room_id));
      }
      if (term) {
        candidateRooms = candidateRooms.filter(
          (r) =>
            r.room_name.toLowerCase().includes(term) ||
            r.room_code.toLowerCase().includes(term) ||
            r.block_name.toLowerCase().includes(term)
        );
      }

      built = candidateRooms
        .slice()
        .sort((a, b) => (a.block_name + a.room_code).localeCompare(b.block_name + b.room_code))
        .map((r) => ({
          key: r.room_id,
          title: r.room_name,
          subtitle: `${r.room_code} · ${r.block_name}`,
          sessionsForLane: daySessions.filter((s) => s.room_id === r.room_id),
        }));
    } else {
      const idField = { cohort: "cohort_id", faculty: "faculty_id", module: "module_id" }[groupBy];
      const nameField = {
        cohort: "cohort_name",
        faculty: "faculty_name",
        module: "module_code",
      }[groupBy];
      const subField = { cohort: null, faculty: null, module: "module_name" }[groupBy];

      const seen = new Map();
      for (const s of daySessions) {
        if (!seen.has(s[idField])) {
          seen.set(s[idField], {
            key: s[idField],
            title: s[nameField],
            subtitle: subField ? s[subField] : null,
            sessionsForLane: [],
          });
        }
        seen.get(s[idField]).sessionsForLane.push(s);
      }

      built = Array.from(seen.values()).sort((a, b) => a.title.localeCompare(b.title));

      if (term) {
        built = built.filter(
          (l) =>
            l.title.toLowerCase().includes(term) ||
            (l.subtitle && l.subtitle.toLowerCase().includes(term))
        );
      }
    }

    if (conflictsOnly) {
      built = built.filter((l) => l.sessionsForLane.some(hasIssue));
    }

    return built;
  }, [groupBy, rooms, daySessions, blockFilter, showAllRooms, searchTerm, conflictsOnly, conflictMap, warningMap]);

  const selectedSession = sessions.find((s) => s.session_id === selectedSessionId) || null;

  const suggestions = useMemo(() => {
    if (!selectedSession) return [];

    const candidates = rooms.filter(
      (r) =>
        r.block_name === selectedSession.block_name &&
        r.room_id !== selectedSession.room_id &&
        r.capacity >= selectedSession.cohort_size
    );

    return candidates
      .filter(
        (r) => !sessions.some((s2) => s2.room_id === r.room_id && timesOverlap(s2, selectedSession))
      )
      .slice(0, 2)
      .map((r) => ({
        label: `${r.room_name} (${r.room_code}) → ${selectedSession.day_of_week} ${selectedSession.start_time}`,
        tag: r.capacity >= selectedSession.cohort_size ? "Resolves overflow" : "No conflicts",
      }));
  }, [selectedSession, rooms, sessions]);

  async function handleAutoArrange() {
    try {
      setResolving(true);
      setResolveNotice("");

      const response = await fetch(`${API}/timetable/auto-resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day: selectedDay }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to auto-resolve");
      }

      if (data.resolvedCount === 0) {
        setResolveNotice("Nothing to resolve.");
      } else {
        setResolveNotice(
          `✓ Resolved ${data.resolvedCount} issue${data.resolvedCount !== 1 ? "s" : ""} on ${selectedDay}.`
        );
      }

      setSelectedSessionId(null);
      await loadAll();
    } catch (err) {
      setResolveNotice(`✗ ${err.message}`);
    } finally {
      setResolving(false);
    }
  }

  function blockStyle(sessionId) {
    if (conflictMap.has(sessionId)) return "conflict";
    if (warningMap.has(sessionId)) return "warning";
    return "scheduled";
  }

  function topPct(startTime) {
    return Math.max(0, ((toMinutes(startTime) - DAY_START_MIN) / DAY_SPAN_MIN) * 100);
  }

  function heightPct(startTime, endTime) {
    return ((toMinutes(endTime) - toMinutes(startTime)) / DAY_SPAN_MIN) * 100;
  }

  return (
    <div className="studio">
      <div className="studio-page-header">
        <div>
          <h2>Timetable Studio</h2>
          <p className="studio-page-subtitle">
            {selectedDay} · {lanes.length} lane{lanes.length !== 1 ? "s" : ""} · {daySessions.length}{" "}
            session{daySessions.length !== 1 ? "s" : ""}
            {toResolveCount > 0 && <span className="resolve-chip"> ⚠ {toResolveCount} to resolve</span>}
          </p>
        </div>

        <div className="group-tabs">
          {["room", "cohort", "faculty", "module"].map((g) => (
            <button
              key={g}
              className={groupBy === g ? "group-tab active" : "group-tab"}
              onClick={() => setGroupBy(g)}
            >
              By {g.charAt(0).toUpperCase() + g.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="error-message">❌ {error}</div>}

      {loading ? (
        <p>Loading timetable studio...</p>
      ) : (
        <div className="studio-body">
          <aside className="canvas-controls">
            <div className="cc-label">Canvas controls</div>

            <div className="cc-block">
              <div className="cc-subheading">Day</div>
              <div className="day-tabs">
                {DAYS.map((d) => (
                  <button
                    key={d.key}
                    className={selectedDay === d.key ? "day-tab active" : "day-tab"}
                    title={d.key}
                    onClick={() => {
                      setSelectedDay(d.key);
                      setSelectedSessionId(null);
                      setResolveNotice("");
                    }}
                  >
                    {d.letter}
                  </button>
                ))}
              </div>
            </div>

            {groupBy === "room" && (
              <div className="cc-block">
                <div className="cc-subheading">Rooms</div>
                <select
                  className="block-select full"
                  value={blockFilter}
                  onChange={(e) => setBlockFilter(e.target.value)}
                >
                  {blockNames.map((b) => (
                    <option key={b} value={b}>
                      {b === "All" ? "All blocks" : b}
                    </option>
                  ))}
                </select>
                <label className="cc-toggle-row">
                  <input
                    type="checkbox"
                    checked={showAllRooms}
                    onChange={(e) => setShowAllRooms(e.target.checked)}
                  />
                  Show all {rooms.length} rooms
                </label>
              </div>
            )}

            <div className="cc-block">
              <div className="cc-subheading">Overlays</div>
              <label className="cc-toggle-row">
                <span>Utilization bands</span>
                <span
                  className={`toggle-pill ${showUtilization ? "on" : ""}`}
                  onClick={() => setShowUtilization((v) => !v)}
                >
                  <span className="toggle-knob" />
                </span>
              </label>
              <label className="cc-toggle-row">
                <span>Conflicts only</span>
                <span
                  className={`toggle-pill ${conflictsOnly ? "on" : ""}`}
                  onClick={() => setConflictsOnly((v) => !v)}
                >
                  <span className="toggle-knob" />
                </span>
              </label>
            </div>

            <div className="cc-block">
              <div className="cc-subheading">Legend</div>
              <div className="legend-list">
                <span><i className="dot scheduled" /> Scheduled</span>
                <span><i className="dot warning" /> Capacity warning</span>
                <span><i className="dot conflict" /> Conflict</span>
              </div>
            </div>

            <div className="auto-arrange-card">
              <div className="aa-icon">✨</div>
              <p className="aa-title">Auto-arrange</p>
              <p className="aa-desc">
                Let Nexus resolve {toResolveCount > 0 ? toResolveCount : "any"} issue
                {toResolveCount !== 1 ? "s" : ""} on {selectedDay} by moving sessions to free rooms
                or times.
              </p>
              <button className="aa-button" onClick={handleAutoArrange} disabled={resolving}>
                {resolving ? "Resolving..." : "Resolve conflicts"}
              </button>
              {resolveNotice && <p className="aa-notice">{resolveNotice}</p>}
            </div>
          </aside>

          <div className="studio-canvas-wrap">
            {lanes.length === 0 ? (
              <div className="error-message">
                No sessions to show for {selectedDay}
                {groupBy === "room" ? " with this filter." : "."}
              </div>
            ) : (
              <div className="lanes-scroll">
                <div className="time-axis">
                  {HOUR_MARKS.map((h) => (
                    <div
                      key={h}
                      className="hour-mark"
                      style={{ top: `${((h * 60 - DAY_START_MIN) / DAY_SPAN_MIN) * 100}%` }}
                    >
                      {String(h).padStart(2, "0")}:00
                    </div>
                  ))}
                </div>

                <div className="lanes">
                  {lanes.map((lane) => {
                    const utilizationMin = lane.sessionsForLane.reduce(
                      (sum, s) => sum + (toMinutes(s.end_time) - toMinutes(s.start_time)),
                      0
                    );
                    const utilizationPct = Math.round((utilizationMin / DAY_SPAN_MIN) * 100);

                    return (
                      <div className="lane" key={lane.key}>
                        <div className="lane-header">
                          <div className="lane-title">{lane.title}</div>
                          {lane.subtitle && <div className="lane-subtitle">{lane.subtitle}</div>}
                          {showUtilization && (
                            <>
                              <div className="lane-util-track">
                                <div
                                  className="lane-util-fill"
                                  style={{ width: `${Math.min(100, utilizationPct)}%` }}
                                />
                              </div>
                              <div className="lane-util-label">{utilizationPct}%</div>
                            </>
                          )}
                        </div>

                        <div className="lane-track">
                          {HOUR_MARKS.slice(0, -1).map((h) => (
                            <div
                              key={h}
                              className="hour-gridline"
                              style={{ top: `${((h * 60 - DAY_START_MIN) / DAY_SPAN_MIN) * 100}%` }}
                            />
                          ))}

                          {layoutOverlaps(lane.sessionsForLane).map(({ session: s, col, totalCols }) => (
                            <button
                              key={s.session_id}
                              className={`session-block ${blockStyle(s.session_id)} ${
                                selectedSessionId === s.session_id ? "active" : ""
                              }`}
                              style={{
                                top: `${topPct(s.start_time)}%`,
                                height: `${Math.max(heightPct(s.start_time, s.end_time), 6)}%`,
                                left: `calc(${(col / totalCols) * 100}% + 2px)`,
                                width: `calc(${(1 / totalCols) * 100}% - 4px)`,
                              }}
                              onClick={() => setSelectedSessionId(s.session_id)}
                            >
                              <strong>{s.module_code}</strong>
                              <span>{s.module_name}</span>
                              <small>{groupBy === "room" ? s.faculty_name : s.room_name}</small>
                              {(conflictMap.has(s.session_id) || warningMap.has(s.session_id)) && (
                                <em className="warn-icon">⚠</em>
                              )}
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <div className="detail-panel">
            {!selectedSession ? (
              <div className="detail-empty">
                <p>Select a session to see its details.</p>
              </div>
            ) : (
              <>
                <div className="detail-header">
                  <span
                    className={
                      conflictMap.has(selectedSession.session_id)
                        ? "detail-kicker conflict"
                        : warningMap.has(selectedSession.session_id)
                        ? "detail-kicker warning"
                        : "detail-kicker"
                    }
                  >
                    {conflictMap.has(selectedSession.session_id)
                      ? "● CONFLICT"
                      : warningMap.has(selectedSession.session_id)
                      ? "● WARNING"
                      : "● SESSION"}
                  </span>
                  <button className="detail-close" onClick={() => setSelectedSessionId(null)}>
                    ✕
                  </button>
                </div>

                <h3>{selectedSession.module_code}</h3>
                <p className="detail-subtitle">{selectedSession.module_name}</p>

                <div className="detail-grid">
                  <div>
                    <span className="detail-label">FACULTY</span>
                    <span className="detail-value">{selectedSession.faculty_name}</span>
                  </div>
                  <div>
                    <span className="detail-label">ROOM</span>
                    <span className="detail-value">{selectedSession.room_name}</span>
                  </div>
                  <div>
                    <span className="detail-label">COHORT</span>
                    <span className="detail-value">{selectedSession.cohort_name}</span>
                  </div>
                  <div>
                    <span className="detail-label">TIME</span>
                    <span className="detail-value">
                      {selectedSession.day_of_week} {selectedSession.start_time}
                    </span>
                  </div>
                </div>

                <div className="detail-capacity">
                  <div className="detail-capacity-header">
                    <span>Capacity</span>
                    <span>
                      {selectedSession.cohort_size} / {selectedSession.room_capacity}
                    </span>
                  </div>
                  <div className="capacity-bar-track">
                    <div
                      className={
                        selectedSession.cohort_size > selectedSession.room_capacity
                          ? "capacity-bar-fill over"
                          : "capacity-bar-fill"
                      }
                      style={{
                        width: `${Math.min(
                          100,
                          (selectedSession.cohort_size / selectedSession.room_capacity) * 100
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                {(conflictMap.get(selectedSession.session_id) || [])
                  .concat(warningMap.get(selectedSession.session_id) || []).length > 0 && (
                  <div className="detail-issues">
                    <p className="detail-issues-title">⚠ Issues detected</p>
                    {(conflictMap.get(selectedSession.session_id) || [])
                      .concat(warningMap.get(selectedSession.session_id) || [])
                      .map((c, i) => (
                        <div className="issue-card" key={i}>
                          <strong>{c.type.replaceAll("_", " ")}</strong>
                          <p>{c.message}</p>
                        </div>
                      ))}
                  </div>
                )}

                {suggestions.length > 0 && (
                  <div className="detail-suggestions">
                    <p className="detail-issues-title">Suggested alternatives</p>
                    {suggestions.map((s, i) => (
                      <div className="suggestion-card" key={i}>
                        <span>{s.label}</span>
                        <span className="suggestion-tag">{s.tag}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default TimetableStudio;

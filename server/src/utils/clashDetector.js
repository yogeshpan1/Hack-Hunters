function timesOverlap(entry1, entry2) {
  return (
    entry1.day_of_week === entry2.day_of_week &&
    entry1.start_time < entry2.end_time &&
    entry2.start_time < entry1.end_time
  );
}

export function detectClashes(entries) {
  const clashes = [];

  for (let i = 0; i < entries.length; i++) {
    for (let j = i + 1; j < entries.length; j++) {
      const entry1 = entries[i];
      const entry2 = entries[j];

      // Only compare sessions happening at the same time
      if (!timesOverlap(entry1, entry2)) {
        continue;
      }

      // --------------------------------
      // ROOM CLASH
      // --------------------------------
      if (entry1.room_id === entry2.room_id) {
        clashes.push({
          type: "ROOM_CLASH",
          session1: entry1.session_id,
          session2: entry2.session_id,
          message: `${entry1.room_name} is being used by ${entry1.module_code} and ${entry2.module_code} at the same time.`,
        });
      }

      // --------------------------------
      // FACULTY CLASH
      // --------------------------------
      if (entry1.faculty_id === entry2.faculty_id) {
        clashes.push({
          type: "FACULTY_CLASH",
          session1: entry1.session_id,
          session2: entry2.session_id,
          message: `${entry1.faculty_name} is assigned to two sessions at the same time.`,
        });
      }

      // --------------------------------
      // COHORT CLASH
      // --------------------------------
      if (entry1.cohort_id === entry2.cohort_id) {
        clashes.push({
          type: "COHORT_CLASH",
          session1: entry1.session_id,
          session2: entry2.session_id,
          message: `${entry1.cohort_name} has two sessions at the same time.`,
        });
      }
    }
  }

  return clashes;
}

// ============================================================
// ROOM CAPACITY CLASH
// ============================================================

export function detectCapacityClashes(entries) {
  const clashes = [];

  for (const entry of entries) {
    if (entry.cohort_size > entry.room_capacity) {
      clashes.push({
        type: "CAPACITY_CLASH",
        session: entry.session_id,
        message: `${entry.room_name} has capacity ${entry.room_capacity}, but ${entry.cohort_name} has ${entry.cohort_size} students.`,
      });
    }
  }

  return clashes;
}

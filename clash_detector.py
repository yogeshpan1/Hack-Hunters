def times_overlap(entry1, entry2):

    return (
        entry1["day_of_week"] == entry2["day_of_week"]
        and entry1["start_time"] < entry2["end_time"]
        and entry2["start_time"] < entry1["end_time"]
    )


def detect_clashes(entries):

    clashes = []

    for i in range(len(entries)):

        for j in range(i + 1, len(entries)):

            entry1 = entries[i]
            entry2 = entries[j]

            # Only compare sessions happening at the same time
            if not times_overlap(entry1, entry2):
                continue

            # --------------------------------
            # ROOM CLASH
            # --------------------------------

            if entry1["room_id"] == entry2["room_id"]:

                clashes.append({
                    "type": "ROOM_CLASH",
                    "session1": entry1["session_id"],
                    "session2": entry2["session_id"],
                    "message": (
                        f"{entry1['room_name']} is being used by "
                        f"{entry1['module_code']} and "
                        f"{entry2['module_code']} at the same time."
                    )
                })

            # --------------------------------
            # FACULTY CLASH
            # --------------------------------

            if entry1["faculty_id"] == entry2["faculty_id"]:

                clashes.append({
                    "type": "FACULTY_CLASH",
                    "session1": entry1["session_id"],
                    "session2": entry2["session_id"],
                    "message": (
                        f"{entry1['faculty_name']} is assigned to "
                        f"two sessions at the same time."
                    )
                })

            # --------------------------------
            # COHORT CLASH
            # --------------------------------

            if entry1["cohort_id"] == entry2["cohort_id"]:

                clashes.append({
                    "type": "COHORT_CLASH",
                    "session1": entry1["session_id"],
                    "session2": entry2["session_id"],
                    "message": (
                        f"{entry1['cohort_name']} has two sessions "
                        f"at the same time."
                    )
                })

    return clashes


# ============================================================
# ROOM CAPACITY CLASH
# ============================================================

def detect_capacity_clashes(entries):

    clashes = []

    for entry in entries:

        if entry["cohort_size"] > entry["room_capacity"]:

            clashes.append({
                "type": "CAPACITY_CLASH",
                "session": entry["session_id"],
                "message": (
                    f"{entry['room_name']} has capacity "
                    f"{entry['room_capacity']}, but "
                    f"{entry['cohort_name']} has "
                    f"{entry['cohort_size']} students."
                )
            })

    return clashes
from data.dbConnection import get_connection



def create_timetable_entry(
    module_id,
    faculty_id,
    cohort_id,
    room_id,
    time_slot_id,
    session_type="LECTURE"
):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        INSERT INTO timetable_sessions
        (
            module_id,
            faculty_id,
            cohort_id,
            room_id,
            time_slot_id,
            session_type
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (
            module_id,
            faculty_id,
            cohort_id,
            room_id,
            time_slot_id,
            session_type
        )
    )

    connection.commit()

    session_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return session_id



def get_all_timetable_entries():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            ts.session_id,

            m.module_id,
            m.module_code,
            m.module_name,

            f.faculty_id,
            f.name AS faculty_name,

            c.cohort_id,
            c.cohort_name,
            c.size AS cohort_size,

            r.room_id,
            r.room_name,
            r.capacity AS room_capacity,

            t.time_slot_id,
            t.day_of_week,
            t.start_time,
            t.end_time,

            ts.session_type

        FROM timetable_sessions ts

        JOIN modules m
            ON ts.module_id = m.module_id

        JOIN faculty f
            ON ts.faculty_id = f.faculty_id

        JOIN cohorts c
            ON ts.cohort_id = c.cohort_id

        JOIN rooms r
            ON ts.room_id = r.room_id

        JOIN time_slots t
            ON ts.time_slot_id = t.time_slot_id

        ORDER BY
            FIELD(
                t.day_of_week,
                'Monday',
                'Tuesday',
                'Wednesday',
                'Thursday',
                'Friday'
            ),
            t.start_time
    """

    cursor.execute(query)

    entries = cursor.fetchall()

    cursor.close()
    connection.close()

    return entries



def get_timetable_entry(session_id):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            ts.session_id,

            m.module_id,
            m.module_code,
            m.module_name,

            f.faculty_id,
            f.name AS faculty_name,

            c.cohort_id,
            c.cohort_name,
            c.size AS cohort_size,

            r.room_id,
            r.room_name,
            r.capacity AS room_capacity,

            t.time_slot_id,
            t.day_of_week,
            t.start_time,
            t.end_time,

            ts.session_type

        FROM timetable_sessions ts

        JOIN modules m
            ON ts.module_id = m.module_id

        JOIN faculty f
            ON ts.faculty_id = f.faculty_id

        JOIN cohorts c
            ON ts.cohort_id = c.cohort_id

        JOIN rooms r
            ON ts.room_id = r.room_id

        JOIN time_slots t
            ON ts.time_slot_id = t.time_slot_id

        WHERE ts.session_id = %s
    """

    cursor.execute(query, (session_id,))

    entry = cursor.fetchone()

    cursor.close()
    connection.close()

    return entry



def update_timetable_entry(
    session_id,
    module_id,
    faculty_id,
    cohort_id,
    room_id,
    time_slot_id,
    session_type
):

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        UPDATE timetable_sessions
        SET
            module_id = %s,
            faculty_id = %s,
            cohort_id = %s,
            room_id = %s,
            time_slot_id = %s,
            session_type = %s

        WHERE session_id = %s
    """

    cursor.execute(
        query,
        (
            module_id,
            faculty_id,
            cohort_id,
            room_id,
            time_slot_id,
            session_type,
            session_id
        )
    )

    connection.commit()

    cursor.close()
    connection.close()



def delete_timetable_entry(session_id):

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        DELETE FROM timetable_sessions
        WHERE session_id = %s
    """

    cursor.execute(query, (session_id,))

    connection.commit()

    cursor.close()
    connection.close()



def get_timetable_for_clash_detection():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            ts.session_id,

            m.module_id,
            m.module_code,
            m.module_name,

            f.faculty_id,
            f.name AS faculty_name,

            c.cohort_id,
            c.cohort_name,
            c.size AS cohort_size,

            r.room_id,
            r.room_name,
            r.capacity AS room_capacity,

            t.time_slot_id,
            t.day_of_week,
            t.start_time,
            t.end_time,

            ts.session_type

        FROM timetable_sessions ts

        JOIN modules m
            ON ts.module_id = m.module_id

        JOIN faculty f
            ON ts.faculty_id = f.faculty_id

        JOIN cohorts c
            ON ts.cohort_id = c.cohort_id

        JOIN rooms r
            ON ts.room_id = r.room_id

        JOIN time_slots t
            ON ts.time_slot_id = t.time_slot_id

        ORDER BY
            FIELD(
                t.day_of_week,
                'Monday',
                'Tuesday',
                'Wednesday',
                'Thursday',
                'Friday'
            ),
            t.start_time
    """

    cursor.execute(query)

    entries = cursor.fetchall()

    # Convert MySQL time values into normal strings
    for entry in entries:

        start_time = entry["start_time"]
        end_time = entry["end_time"]

        if hasattr(start_time, "total_seconds"):
            total_seconds = int(start_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            entry["start_time"] = f"{hours:02d}:{minutes:02d}"

        else:
            entry["start_time"] = str(start_time)[:5]

        if hasattr(end_time, "total_seconds"):
            total_seconds = int(end_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            entry["end_time"] = f"{hours:02d}:{minutes:02d}"

        else:
            entry["end_time"] = str(end_time)[:5]

    cursor.close()
    connection.close()

    return entries
from dbConnection import get_connection


def create_room(room_name, capacity):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO rooms (room_name, capacity)
        VALUES (%s, %s)
        """,
        (room_name, capacity)
    )

    connection.commit()

    cursor.close()
    connection.close()


def get_all_rooms():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM rooms")
    rooms = cursor.fetchall()

    cursor.close()
    connection.close()

    return rooms


def get_room(room_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM rooms WHERE room_id = %s",
        (room_id,)
    )

    room = cursor.fetchone()

    cursor.close()
    connection.close()

    return room


def update_room(room_id, room_name, capacity):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE rooms
        SET room_name = %s, capacity = %s
        WHERE room_id = %s
        """,
        (room_name, capacity, room_id)
    )

    connection.commit()

    cursor.close()
    connection.close()


def delete_room(room_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM rooms WHERE room_id = %s",
        (room_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()
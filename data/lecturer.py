from dbConnection import get_connection


def create_lecturer(name):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO lecturers (name) VALUES (%s)",
        (name,)
    )

    connection.commit()

    cursor.close()
    connection.close()


def get_all_lecturers():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM lecturers")
    lecturers = cursor.fetchall()

    cursor.close()
    connection.close()

    return lecturers


def get_lecturer(lecturer_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM lecturers WHERE lecturer_id = %s",
        (lecturer_id,)
    )

    lecturer = cursor.fetchone()

    cursor.close()
    connection.close()

    return lecturer


def update_lecturer(lecturer_id, name):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE lecturers SET name = %s WHERE lecturer_id = %s",
        (name, lecturer_id)
    )

    connection.commit()

    cursor.close()
    connection.close()


def delete_lecturer(lecturer_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM lecturers WHERE lecturer_id = %s",
        (lecturer_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()
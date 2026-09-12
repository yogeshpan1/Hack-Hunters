from data.dbConnection import get_connection


def create_course(course_code, course_name):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        INSERT INTO courses (course_code, course_name)
        VALUES (%s, %s)
    """

    cursor.execute(query, (course_code, course_name))
    connection.commit()

    cursor.close()
    connection.close()


def get_all_courses():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    cursor.close()
    connection.close()

    return courses


def get_course(course_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM courses WHERE course_id = %s",
        (course_id,)
    )

    course = cursor.fetchone()

    cursor.close()
    connection.close()

    return course


def update_course(course_id, course_code, course_name):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        UPDATE courses
        SET course_code = %s, course_name = %s
        WHERE course_id = %s
    """

    cursor.execute(query, (course_code, course_name, course_id))
    connection.commit()

    cursor.close()
    connection.close()


def delete_course(course_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM courses WHERE course_id = %s",
        (course_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()
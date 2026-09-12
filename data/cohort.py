from dbConnection import get_connection


def create_cohort(cohort_name, size):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO cohorts (cohort_name, size)
        VALUES (%s, %s)
        """,
        (cohort_name, size)
    )

    connection.commit()

    cursor.close()
    connection.close()


def get_all_cohorts():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM cohorts")
    cohorts = cursor.fetchall()

    cursor.close()
    connection.close()

    return cohorts


def get_cohort(cohort_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM cohorts WHERE cohort_id = %s",
        (cohort_id,)
    )

    cohort = cursor.fetchone()

    cursor.close()
    connection.close()

    return cohort


def update_cohort(cohort_id, cohort_name, size):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE cohorts
        SET cohort_name = %s, size = %s
        WHERE cohort_id = %s
        """,
        (cohort_name, size, cohort_id)
    )

    connection.commit()

    cursor.close()
    connection.close()


def delete_cohort(cohort_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM cohorts WHERE cohort_id = %s",
        (cohort_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()
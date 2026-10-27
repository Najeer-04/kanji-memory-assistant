
from backend.database import get_connection

with get_connection() as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), version()")
        result = cursor.fetchone()

        print("Connected to:", result[0])
        print("PostgreSQL version:", result[1].split(",")[0])

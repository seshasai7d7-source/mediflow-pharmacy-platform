
from sqlalchemy import text
from app.db.database import engine


def check_database_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.scalar()

            print("Database connection successful!")
            print(f"PostgreSQL version: {version}")

    except Exception as error:
        print("Database connection failed!")
        print(f"Error: {error}")


if __name__ == "__main__":
    check_database_connection()

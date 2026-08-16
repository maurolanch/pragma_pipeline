import os

from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Create and return a PostgreSQL database connection."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

def create_tables(connection):
    """Create the database tables required by the pipeline."""

    sql_path = Path(__file__).parent.parent / "sql" / "create_tables.sql"

    with open(sql_path, "r") as file:
        sql = file.read()

    with connection.cursor() as cursor:
        cursor.execute(sql)

    connection.commit()
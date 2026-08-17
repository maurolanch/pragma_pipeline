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

def is_batch_processed(connection, source_file):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM processed_batches
            WHERE source_file = %s;
            """,
            (source_file,),
        )

        return cursor.fetchone() is not None


def mark_batch_processed(connection, source_file):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO processed_batches (source_file)
            VALUES (%s);
            """,
            (source_file,),
        )
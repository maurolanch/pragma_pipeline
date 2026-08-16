from pathlib import Path

from pipeline.db import get_connection, create_tables
from pipeline.ingester import load_csv_to_db


def main():
    connection = get_connection()

    create_tables(connection)

    data_path = Path("data")

    csv_files = sorted(data_path.glob("2012-*.csv"))

    for file_path in csv_files:
        load_csv_to_db(connection, file_path)

    connection.close()


if __name__ == "__main__":
    main()
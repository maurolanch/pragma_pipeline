import pandas as pd

from pipeline.logger import get_logger

logger = get_logger(__name__)


def load_csv_to_db(connection, file_path):
    logger.info("Starting ingestion: %s", file_path.name)

    df = pd.read_csv(file_path)

    logger.info(
        "CSV loaded: %s rows from %s",
        len(df),
        file_path.name
    )

    with connection.cursor() as cursor:
        for _, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO transactions (
                    timestamp,
                    price,
                    user_id,
                    source_file
                )
                VALUES (%s, %s, %s, %s);
                """,
                (
                    row["timestamp"],
                    row["price"] if pd.notna(row["price"]) else None,
                    row["user_id"],
                    file_path.name,
                ),
            )

    connection.commit()

    logger.info(
        "Ingestion completed: %s rows inserted from %s",
        len(df),
        file_path.name
    )
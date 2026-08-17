from pathlib import Path

from pipeline.logger import get_logger
from pipeline.db import get_connection, create_tables, is_batch_processed, mark_batch_processed
from pipeline.ingester import load_csv_to_db
from pipeline.stats import calculate_batch_stats, update_stats, get_current_stats

logger = get_logger(__name__)

def main():
    connection = get_connection()

    create_tables(connection)

    data_path = Path("data")

    csv_files = sorted(data_path.glob("2012-*.csv"))

    for file_path in csv_files:

        if is_batch_processed(connection, file_path.name):
            logger.info(
                "Skipping already processed batch: %s",
                file_path.name
            )
            continue

        try:
            df = load_csv_to_db(connection, file_path)

            batch_stats = calculate_batch_stats(df)

            current_stats = update_stats(
                connection,
                batch_stats
            )

            mark_batch_processed(
                connection,
                file_path.name
            )

            connection.commit()

            logger.info(
                "Batch completed: %s | stats=%s",
                file_path.name,
                current_stats
            )

        except Exception:
            connection.rollback()

            logger.exception(
                "Batch failed: %s",
                file_path.name
            )

            raise

    current_stats = get_current_stats(connection)

    logger.info(
        "Current pipeline stats before validation: %s",
        current_stats
    )

    validation_path = data_path / "validation.csv"

    if is_batch_processed(connection, validation_path.name):
        logger.info(
            "Skipping already processed batch: %s",
            validation_path.name
        )
    else:
        try:
            df = load_csv_to_db(connection, validation_path)

            batch_stats = calculate_batch_stats(df)

            current_stats = update_stats(
                connection,
                batch_stats
            )

            mark_batch_processed(
                connection,
                validation_path.name
            )

            connection.commit()

            logger.info(
                "Validation completed: stats=%s",
                current_stats
            )

        except Exception:
            connection.rollback()

            logger.exception(
                "Validation failed: %s",
                validation_path.name
            )

            raise
    connection.close()


if __name__ == "__main__":
    main()
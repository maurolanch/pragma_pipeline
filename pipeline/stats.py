import pandas as pd
from decimal import Decimal

def calculate_batch_stats(df):
    prices = df["price"].dropna()

    total_sum = sum(
        (Decimal(str(price)) for price in prices),
        Decimal("0")
    )

    min_price = (
        Decimal(str(prices.min()))
        if not prices.empty
        else None
    )

    max_price = (
        Decimal(str(prices.max()))
        if not prices.empty
        else None
    )

    return {
        "row_count": int(len(df)),
        "total_sum": total_sum,
        "min_price": min_price,
        "max_price": max_price,
    }


def update_stats(connection, batch_stats):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT row_count, total_sum, min_price, max_price
            FROM pipeline_stats
            WHERE id = 1;
            """
        )

        previous_stats = cursor.fetchone()

        if previous_stats is None:

            accumulated_count = batch_stats["row_count"]
            accumulated_sum = batch_stats["total_sum"]
            accumulated_min = batch_stats["min_price"]
            accumulated_max = batch_stats["max_price"]

        else:

            previous_count, previous_sum, previous_min, previous_max = previous_stats

            accumulated_count = (
                previous_count + batch_stats["row_count"]
            )

            accumulated_sum = (
                previous_sum + batch_stats["total_sum"]
            )

            accumulated_min = min(
                previous_min,
                batch_stats["min_price"]
            )

            accumulated_max = max(
                previous_max,
                batch_stats["max_price"]
            )

            accumulated_avg = (
                accumulated_sum / Decimal(accumulated_count)
                if accumulated_count > 0
                else None
            )

        cursor.execute(
            """
            INSERT INTO pipeline_stats (
                id,
                row_count,
                total_sum,
                min_price,
                max_price,
                avg_price
            )
            VALUES (1, %s, %s, %s, %s, %s)

            ON CONFLICT (id)
            DO UPDATE SET
                row_count = EXCLUDED.row_count,
                total_sum = EXCLUDED.total_sum,
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                avg_price = EXCLUDED.avg_price,
                updated_at = NOW();
            """,
            (
                accumulated_count,
                accumulated_sum,
                accumulated_min,
                accumulated_max,
                accumulated_avg,
            ),
        )

    connection.commit()

    return {
        "row_count": accumulated_count,
        "total_sum": accumulated_sum,
        "min_price": accumulated_min,
        "max_price": accumulated_max,
        "avg_price": accumulated_avg,
    }
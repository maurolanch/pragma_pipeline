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
        "price_count": int(len(prices)),
        "total_sum": total_sum,
        "min_price": min_price,
        "max_price": max_price,
    }


def update_stats(connection, batch_stats):
    from decimal import Decimal

    with connection.cursor() as cursor:

        # Get the current cumulative state
        cursor.execute(
            """
            SELECT
                row_count,
                price_count,
                total_sum,
                min_price,
                max_price
            FROM pipeline_stats
            WHERE id = 1
            """
        )

        previous_stats = cursor.fetchone()

        # No previous state: first batch
        if previous_stats is None:
            previous_count = 0
            previous_price_count = 0
            previous_sum = Decimal("0")
            previous_min = None
            previous_max = None

        else:
            (
                previous_count,
                previous_price_count,
                previous_sum,
                previous_min,
                previous_max,
            ) = previous_stats

        # Accumulate row counts
        accumulated_count = (
            previous_count + batch_stats["row_count"]
        )

        accumulated_price_count = (
            previous_price_count + batch_stats["price_count"]
        )

        # Accumulate sum
        accumulated_sum = (
            previous_sum
            + batch_stats["total_sum"]
        )

        # Accumulate minimum
        batch_min = batch_stats["min_price"]

        if previous_min is None:
            accumulated_min = batch_min
        elif batch_min is None:
            accumulated_min = previous_min
        else:
            accumulated_min = min(
                previous_min,
                batch_min
            )

        # Accumulate maximum
        batch_max = batch_stats["max_price"]

        if previous_max is None:
            accumulated_max = batch_max
        elif batch_max is None:
            accumulated_max = previous_max
        else:
            accumulated_max = max(
                previous_max,
                batch_max
            )

        # Calculate cumulative average
        if accumulated_price_count > 0:
            accumulated_avg = (
                accumulated_sum
                / Decimal(accumulated_price_count)
            )
        else:
            accumulated_avg = None

        # Persist cumulative state
        cursor.execute(
            """
            INSERT INTO pipeline_stats (
                id,
                row_count,
                price_count,
                total_sum,
                min_price,
                max_price,
                avg_price,
                updated_at
            )
            VALUES (
                1,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW()
            )
            ON CONFLICT (id)
            DO UPDATE SET
                row_count = EXCLUDED.row_count,
                price_count = EXCLUDED.price_count,
                total_sum = EXCLUDED.total_sum,
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                avg_price = EXCLUDED.avg_price,
                updated_at = NOW()
            """,
            (
                accumulated_count,
                accumulated_price_count,
                accumulated_sum,
                accumulated_min,
                accumulated_max,
                accumulated_avg,
            )
        )

    connection.commit()

    return {
        "row_count": accumulated_count,
        "price_count": accumulated_price_count,
        "total_sum": accumulated_sum,
        "min_price": accumulated_min,
        "max_price": accumulated_max,
        "avg_price": accumulated_avg,
    }

def get_current_stats(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                row_count,
                price_count,
                total_sum,
                min_price,
                max_price,
                avg_price
            FROM pipeline_stats
            WHERE id = 1
            """
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "row_count": row[0],
        "price_count": row[1],
        "total_sum": row[2],
        "min_price": row[3],
        "max_price": row[4],
        "avg_price": row[5],
    }

-- Transactions
-- Stores all records ingested from the CSV micro-batches

CREATE TABLE IF NOT EXISTS transactions (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   DATE NOT NULL,
    price       DECIMAL(10,2),
    user_id     INTEGER NOT NULL,
    source_file VARCHAR(50) NOT NULL,
    loaded_at   TIMESTAMP DEFAULT NOW()
);



-- Pipeline statistics
-- Stores the cumulative state of the pipeline


CREATE TABLE IF NOT EXISTS pipeline_stats (
    id          INTEGER PRIMARY KEY,
    row_count   BIGINT NOT NULL,
    total_sum   DECIMAL(15,2) NOT NULL,
    min_price   DECIMAL(10,2),
    max_price   DECIMAL(10,2),
    updated_at  TIMESTAMP DEFAULT NOW()
);


-- Initialize the pipeline state
INSERT INTO pipeline_stats (
    id,
    row_count,
    total_sum,
    min_price,
    max_price
)
VALUES (
    1,
    0,
    0,
    NULL,
    NULL
)
ON CONFLICT (id) DO NOTHING;

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
    avg_price   DECIMAL(15,4),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- Processed batches
-- Guarantees that a closed CSV batch is processed only once

CREATE TABLE IF NOT EXISTS processed_batches (
    source_file VARCHAR(50) PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT NOW()
);
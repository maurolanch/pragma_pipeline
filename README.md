# Pragma Data Engineering Challenge

## Overview

This project implements a data pipeline that ingests CSV files in micro-batches, stores the data in PostgreSQL, and maintains cumulative statistics as new data is processed.

The solution was designed around the main requirements of the challenge:

- Process CSV files incrementally instead of loading all files into memory.
- Store all ingested records in the same database.
- Maintain cumulative statistics without repeatedly querying the entire transactions table.
- Support idempotent execution.
- Handle `NULL` prices correctly.
- Provide logging for pipeline execution and failures.
- Validate the final results against the database contents.

---

## Architecture

The pipeline follows this flow:

```text
CSV files
    |
    v
main.py
    |
    +--------------------+
    |                    |
    v                    v
Ingester              Statistics
    |                    |
    v                    v
PostgreSQL <------- pipeline_stats
    |
    +--> transactions
    |
    +--> processed_batches
```

The pipeline processes one CSV file at a time.

For each batch:

```text
Read CSV
   |
   v
Insert records
   |
   v
Calculate batch statistics
   |
   v
Update cumulative statistics
   |
   v
Mark batch as processed
   |
   v
Commit transaction
```

If an error occurs, the transaction is rolled back.

---

## Project Structure

```text
pragma_pipeline/
│
├── data/
│   ├── 2012-1.csv
│   ├── 2012-2.csv
│   ├── 2012-3.csv
│   ├── 2012-4.csv
│   ├── 2012-5.csv
│   └── validation.csv
│
├── pipeline/
│   ├── db.py
│   ├── ingester.py
│   ├── stats.py
│   └── logger.py
│
├── main.py
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## Database Design

PostgreSQL was selected as the database because the challenge allows any relational database and PostgreSQL provides a simple and reliable solution for this workload.

The pipeline uses three tables:

1. `transactions`
2. `pipeline_stats`
3. `processed_batches`

### 1. `transactions`

This table stores the actual records ingested from the CSV files.

```sql
CREATE TABLE IF NOT EXISTS transactions (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   DATE NOT NULL,
    price       DECIMAL(10,2),
    user_id     INTEGER NOT NULL,
    source_file VARCHAR(50) NOT NULL,
    loaded_at   TIMESTAMP DEFAULT NOW()
);
```

### Design decisions

- `id` is a surrogate primary key.
- `timestamp` stores the event timestamp.
- `price` allows `NULL` values because the input data contains missing prices.
- `source_file` identifies the batch from which each record originated.
- `loaded_at` records when the record was inserted into the database.

---

### 2. `pipeline_stats`

This table stores the current cumulative state of the pipeline.

```sql
CREATE TABLE IF NOT EXISTS pipeline_stats (
    id          INTEGER PRIMARY KEY,
    row_count   BIGINT NOT NULL,
    price_count BIGINT NOT NULL,
    total_sum   DECIMAL(15,2) NOT NULL,
    min_price   DECIMAL(10,2),
    max_price   DECIMAL(10,2),
    avg_price   DECIMAL(15,4),
    updated_at  TIMESTAMP DEFAULT NOW()
);
```

Only one row is maintained in this table.

This was intentional because the challenge requires the pipeline to maintain the current running statistics. It does not require a historical statistics record for every batch.

For example, after processing the five initial files:

```text
row_count   = 143
price_count = 139
total_sum   = 8046.00
min_price   = 10.00
max_price   = 100.00
avg_price   = 57.8849
```

When `validation.csv` is processed, this same row is updated to reflect the new cumulative state.

---

### 3. `processed_batches`

This table is used to guarantee idempotency.

Each successfully processed CSV file is registered in this table.

Before processing a file, the pipeline checks whether the file has already been processed:

```text
Is the batch already processed?
        |
   +----+----+
   |         |
  Yes        No
   |         |
 Skip       Process
             |
             v
       Mark as processed
```

This prevents the same batch from being inserted twice when the pipeline is executed again.

The batch is marked as processed within the same database transaction that inserts the data and updates the statistics.

---

# Micro-Batch Processing

The pipeline does not load all CSV files into memory simultaneously.

Instead, files are discovered and processed sequentially:

```python
csv_files = sorted(data_path.glob("2012-*.csv"))

for file_path in csv_files:
    ...
```

Only the current CSV is loaded into a Pandas DataFrame.

After processing the batch, the next file is loaded.

This follows the micro-batch strategy requested in the challenge and avoids loading the complete dataset into memory at once.

---

# Ingestion

The ingestion logic is implemented in:

```text
pipeline/ingester.py
```

The main responsibilities of the ingester are:

1. Read the current CSV file.
2. Insert its records into PostgreSQL.
3. Return the DataFrame so statistics can be calculated for the current batch.

The source file name is stored with every transaction.

This provides traceability between database records and their original batch.

---

# Incremental Statistics

One of the main design decisions was to avoid executing a full-table aggregation such as:

```sql
SELECT AVG(price)
FROM transactions;
```

after every batch.

Instead, the pipeline maintains cumulative state.

For each batch, the following statistics are calculated:

```text
row_count
price_count
total_sum
min_price
max_price
```

The cumulative values are then updated using the previous state and the new batch statistics.

For example:

```text
previous row_count
        +
current batch row_count
        =
new row_count
```

The same approach is used for the price count and total sum.

The average is derived from the accumulated values:

```text
average = total_sum / price_count
```

Therefore, the complete `transactions` table does not need to be scanned after every batch.

This satisfies the incremental statistics requirement of the challenge.

---

# Handling NULL Prices

The input data contains records where `price` is `NULL`.

For this reason, two different counts are maintained:

```text
row_count
```

represents all rows.

```text
price_count
```

represents only rows with a non-`NULL` price.

For example:

```text
row_count   = 151
price_count = 147
```

This means four records do not have a price.

Price-based statistics such as average, minimum, and maximum therefore consider only the 147 records with valid prices.

---

# Idempotency

The pipeline is designed to be safely executed multiple times.

After the first execution, the processed batches are registered:

```text
2012-1.csv
2012-2.csv
2012-3.csv
2012-4.csv
2012-5.csv
validation.csv
```

Running the pipeline again produces messages such as:

```text
Skipping already processed batch: 2012-1.csv
Skipping already processed batch: 2012-2.csv
Skipping already processed batch: 2012-3.csv
Skipping already processed batch: 2012-4.csv
Skipping already processed batch: 2012-5.csv
Skipping already processed batch: validation.csv
```

The database is therefore not duplicated by repeated executions.

The idempotency strategy is based on the batch/file identifier. This is appropriate for this challenge because the specification states that CSV file names are unique and ordered.

---

# Transactions and Error Handling

Each batch is processed inside a database transaction.

The general sequence is:

```text
Load batch
    |
Insert records
    |
Calculate statistics
    |
Update pipeline statistics
    |
Mark batch as processed
    |
COMMIT
```

If an exception occurs:

```python
connection.rollback()
```

is executed.

The exception is also logged together with the batch name.

This prevents a failed batch from being considered successfully processed.

The transaction boundary is important because the following operations should succeed or fail together:

- Data insertion
- Statistics update
- Batch registration

---

# Logging

The project includes a dedicated logging module:

```text
pipeline/logger.py
```

The pipeline logs:

- Batch start
- Number of rows loaded
- Number of rows inserted
- Batch completion
- Current statistics
- Skipped batches
- Batch failures

Example:

```text
INFO | pipeline.ingester | Starting ingestion: 2012-1.csv
INFO | pipeline.ingester | CSV loaded: 22 rows from 2012-1.csv
INFO | pipeline.ingester | Ingestion completed: 22 rows inserted from 2012-1.csv
INFO | main | Batch completed: 2012-1.csv | stats={...}
```

Logging was separated into its own module so that the pipeline components do not need to configure logging independently.

---

# Validation

After the five main CSV files are processed, the pipeline retrieves the current statistics before loading `validation.csv`.

The initial state was:

```text
row_count   = 143
price_count = 139
total_sum   = 8046.00
min_price   = 10.00
max_price   = 100.00
avg_price   = 57.8849
```

Then `validation.csv` is processed through the same ingestion and statistics logic.

The resulting state is:

```text
row_count   = 151
price_count = 147
total_sum   = 8380.00
min_price   = 10.00
max_price   = 100.00
avg_price   = 57.0068
```

The results were independently verified with a query against the `transactions` table:

```sql
SELECT
    COUNT(*) AS row_count,
    COUNT(price) AS price_count,
    SUM(price) AS total_sum,
    AVG(price) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price
FROM transactions;
```

The database returned:

```text
row_count   = 151
price_count = 147
total_sum   = 8380.00
avg_price   = 57.0068027210884354
min_price   = 10.00
max_price   = 100.00
```

These values are consistent with the cumulative pipeline state.

---

# Edge Cases Considered

The implementation considers the following cases.

### NULL prices

Rows with `NULL` prices are included in `row_count`, but excluded from price-based statistics.

### Repeated execution

Already processed batches are skipped.

### Batch failure

Database changes are rolled back if an exception occurs.

### Empty price set

The statistics logic handles batches without valid prices without attempting to calculate an average, minimum, or maximum from an empty set.

### Validation batch

`validation.csv` is processed through the same ingestion and statistics logic rather than through a separate implementation.

---

# Running the Project

## 1. Install dependencies

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 2. Configure environment variables

Create a `.env` file containing the PostgreSQL connection parameters:

```text
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pragma
DB_USER=pragma
DB_PASSWORD=your_password
```

---

## 3. Start PostgreSQL

If Docker Compose is being used:

```bash
docker compose up -d
```

---

## 4. Run the pipeline

```bash
python main.py
```

The pipeline will process:

```text
2012-1.csv
2012-2.csv
2012-3.csv
2012-4.csv
2012-5.csv
```

and then process:

```text
validation.csv
```

---

# Verifying the Results

The final statistics can be verified directly in PostgreSQL:

```sql
SELECT
    COUNT(*) AS row_count,
    COUNT(price) AS price_count,
    SUM(price) AS total_sum,
    AVG(price) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price
FROM transactions;
```

The cumulative pipeline state can be inspected with:

```sql
SELECT
    row_count,
    price_count,
    total_sum,
    avg_price,
    min_price,
    max_price
FROM pipeline_stats
WHERE id = 1;
```

The two results should represent the same cumulative state, with only the stored precision of `avg_price` potentially differing because `pipeline_stats.avg_price` is stored as `DECIMAL(15,4)`.

---

# Design Decisions Summary

| Requirement | Decision |
|---|---|
| Micro-batches | Process one CSV at a time |
| Database | PostgreSQL |
| Raw data storage | `transactions` table |
| Running statistics | Single-row `pipeline_stats` table |
| Idempotency | `processed_batches` table |
| Average calculation | `total_sum / price_count` |
| NULL handling | `price_count` excludes NULL prices |
| Transactions | Commit after complete batch |
| Failure handling | Rollback and logging |
| Observability | Python logging |
| Validation | `validation.csv` through the same pipeline |
| Performance strategy | Incremental statistics instead of full-table aggregation |

---

# Conclusion

The solution focuses on correctness, incremental processing, transactional consistency, and idempotency rather than introducing unnecessary infrastructure.

The pipeline demonstrates how a batch-oriented process can be divided into smaller micro-batches while maintaining a continuously updated state of the processed data.

The implementation also separates ingestion, database access, statistics, and logging responsibilities into independent modules, making the pipeline easier to understand and extend.
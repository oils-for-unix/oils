-- select * from tasks limit 5;

-- annoying: you have to cast(x as real) for pragma_info to have type info
CREATE TABLE packages AS
  SELECT
    status,
    elapsed_secs,
    CAST(user_secs / elapsed_secs AS REAL) AS user_elapsed_ratio,
    CAST(user_secs / sys_secs AS REAL) AS user_sys_ratio,
    CAST(max_rss_KiB * 1024 / 1e6 AS REAL) AS max_rss_MB,
    pkg,
    pkg_HREF
  FROM tasks;

-- sqlite table schema -> foo.schema.tsv
CREATE TABLE packages_schema AS
  SELECT
    name AS column_name,
    CASE
      WHEN UPPER(type) = "INTEGER" THEN "integer"
      WHEN UPPER(type) = "REAL" THEN "float"
      WHEN UPPER(type) = "TEXT" THEN "string"
      ELSE LOWER(type)
    END AS type
  FROM PRAGMA_TABLE_INFO("packages");

-- select * from packages_schema;

ALTER TABLE packages_schema ADD COLUMN precision;

UPDATE packages_schema SET precision = 1 WHERE column_name = "elapsed_secs";
UPDATE packages_schema
SET precision = 1
WHERE column_name = "user_elapsed_ratio";
UPDATE packages_schema SET precision = 1 WHERE column_name = "user_sys_ratio";
UPDATE packages_schema SET precision = 1 WHERE column_name = "max_rss_MB";

-- Compute stats

CREATE TABLE metrics (
  id INTEGER PRIMARY KEY CHECK (id = 1), -- ensure only one row
  elapsed_minutes REAL NOT NULL,
  num_failures INTEGER NOT NULL,
  num_tasks INTEGER NOT NULL
);

-- dummy row
INSERT INTO metrics VALUES (1, -1.0, -1, -1);

UPDATE metrics
SET elapsed_minutes = (SELECT (max(end_time) - min(start_time)) / 60 FROM tasks)
WHERE id = 1;

UPDATE metrics
SET num_failures = (SELECT count(*) FROM tasks WHERE status != 0)
WHERE id = 1;

UPDATE metrics
SET num_tasks = (SELECT count(*) FROM tasks)
WHERE id = 1;

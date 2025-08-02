-- Attach the source databases
ATTACH DATABASE 'baseline/tables.db' AS baseline;
ATTACH DATABASE 'osh-as-sh/tables.db' AS osh_as_sh;

-- .mode columns
-- select * from packages;

CREATE TABLE diff AS
  SELECT
    b.pkg,
    CAST(b.status AS INTEGER) AS status1,
    "baseline" AS baseline,
    "baseline/" || b.pkg_HREF AS baseline_HREF,
    o.status AS status2,
    "osh-as-sh" AS osh_as_sh,
    "osh-as-sh/" || o.pkg_HREF AS osh_as_sh_HREF,
    "diff" AS diff,
    printf("error/%s.txt", b.pkg) AS diff_HREF,
    "error" AS error_grep,
    printf("error/%s.txt", b.pkg) AS error_grep_HREF
  FROM
    baseline.packages AS b
    JOIN osh_as_sh.packages AS o ON b.pkg = o.pkg
  WHERE b.status != o.status
  ORDER BY b.pkg;

-- Copied from above
CREATE TABLE diff_schema AS
  SELECT
    name AS column_name,
    CASE
      WHEN UPPER(type) = "INTEGER" THEN "integer"
      WHEN UPPER(type) = "REAL" THEN "float"
      WHEN UPPER(type) = "TEXT" THEN "string"
      ELSE LOWER(type)
    END AS type
  FROM PRAGMA_TABLE_INFO("diff");

-- Detach databases
DETACH DATABASE baseline;
DETACH DATABASE osh_as_sh;

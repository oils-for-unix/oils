-- Attach the source databases
ATTACH DATABASE 'baseline/tables.db' AS baseline;
ATTACH DATABASE 'osh-as-sh/tables.db' AS osh_as_sh;

.mode columns
-- select * from packages;

create table diff as
select
  b.pkg,
  cast(b.status as integer) as status1,
  "baseline" as baseline,
  "baseline/" || b.pkg_HREF as baseline_HREF,
  o.status as status2,
  "osh-as-sh" as osh_as_sh,
  "osh-as-sh/" || o.pkg_HREF as osh_as_sh_HREF,
  "diff" as diff,
  printf("error/%s.txt", b.pkg) as diff_HREF,
  "error" as error_grep,
  printf("error/%s.txt", b.pkg) as error_grep_HREF
from baseline.packages b
join osh_as_sh.packages o on b.pkg = o.pkg
where b.status != o.status
order by b.pkg;

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

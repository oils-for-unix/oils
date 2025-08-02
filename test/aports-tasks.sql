-- select * from tasks limit 5;

-- annoying: you have to cast(x as real) for pragma_info to have type info
create table packages as
select status, 
       elapsed_secs,
       cast( user_secs / elapsed_secs as real) as user_elapsed_ratio,
       cast( user_secs / sys_secs as real) as user_sys_ratio,
       cast(max_rss_KiB * 1024 / 1e6 as real) as max_rss_MB,
       pkg, 
       pkg_HREF
from tasks;

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

alter table packages_schema add column precision;

update packages_schema SET precision = 1 where column_name = "elapsed_secs";
update packages_schema SET precision = 1 where column_name = "user_elapsed_ratio";
update packages_schema SET precision = 1 where column_name = "user_sys_ratio";
update packages_schema SET precision = 1 where column_name = "max_rss_MB";

-- Compute stats

CREATE TABLE metrics (
  id integer primary key check (id = 1),  -- ensure only one row
  elapsed_minutes REAL NOT NULL,
  num_failures integer NOT NULL,
  num_tasks integer NOT NULL
);

# dummy row
insert into metrics values (1, -1.0, -1, -1);

update metrics 
set elapsed_minutes = 
(select ( max(end_time)-min(start_time) ) / 60 from tasks)
where id = 1;

update metrics 
set num_failures = 
(select count(*) from tasks where status != 0)
where id = 1;

update metrics 
set num_tasks = 
(select count(*) from tasks)
where id = 1;

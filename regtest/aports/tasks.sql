-- SQL invoked from regtest/aports-html.sh

-- annoying: you have to cast(x as real) for pragma_info to have type info
create table packages as
  select
    status,
    elapsed_secs,
    cast(user_secs / elapsed_secs as real) as user_elapsed_ratio,
    cast(user_secs / sys_secs as real) as user_sys_ratio,
    cast(max_rss_KiB * 1024 / 1e6 as real) as max_rss_MB,
    pkg,
    pkg_HREF
  from tasks;

-- Compute stats

create table metrics (
  id integer primary key check (id = 1), -- ensure only one row

  elapsed_minutes real not null,
  num_failures integer not null,
  num_tasks integer not null,
  -- filled in later
  num_apk integer not null
);

-- dummy row
insert into metrics values (1, -1.0, -1, -1, -1);

update metrics
set elapsed_minutes = (select (max(end_time) - min(start_time)) / 60 from tasks)
where id = 1;

update metrics
set num_failures = (select count(*) from tasks where status != 0)
where id = 1;

update metrics
set num_tasks = (select count(*) from tasks)
where id = 1;

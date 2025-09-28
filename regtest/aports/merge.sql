-- SQL invoked from regtest/aports-html.sh

update diff_merged
set
  baseline_HREF = printf("%s/%s", shard, baseline_HREF),
  osh_as_sh_HREF = printf("%s/%s", shard, osh_as_sh_HREF),
  error_grep_HREF = printf("%s/%s", shard, error_grep_HREF),
  -- note: suite/suite_HREF are sometimes empty
  suite_HREF = printf("%s/%s", shard, suite_HREF);

-- Useful queries to verify the result:
-- SELECT COUNT(*) as total_rows FROM diff_merged;
-- SELECT shard, COUNT(*) as row_count FROM diff_merged GROUP BY shard ORDER BY shard;
-- .schema diff_merged

create table notable_disagree as
  select *
  from diff_merged
  where disagree == 1 and status1 == 0 and timeout == 0;

create table baseline_only as
  select *
  from diff_merged
  where disagree == 1 and status2 == 0 and timeout == 0;

create table other_fail as
  select *
  from diff_merged
  where disagree == 0 and timeout == 0;

create table timeout as
  select *
  from diff_merged
  where timeout == 1;

-- drop 2 columns from each of 3 tables (sqlite is verbose)

alter table notable_disagree
drop column disagree;
alter table notable_disagree
drop column timeout;

alter table baseline_only
drop column disagree;
alter table baseline_only
drop column timeout;

alter table other_fail
drop column disagree;
alter table other_fail
drop column timeout;

alter table timeout
drop column disagree;
alter table timeout
drop column timeout;

-- SQL invoked from regtest/aports-html.sh

update diff_merged
set
  baseline_HREF = printf("%s/%s", shard, baseline_HREF),
  osh_as_sh_HREF = printf("%s/%s", shard, osh_as_sh_HREF),
  error_grep_HREF = printf("%s/%s", shard, error_grep_HREF);

-- Useful queries to verify the result:
-- SELECT COUNT(*) as total_rows FROM diff_merged;
-- SELECT shard, COUNT(*) as row_count FROM diff_merged GROUP BY shard ORDER BY shard;
-- .schema diff_merged

create table notable_disagree as
  select *
  from diff_merged
  where notable == 1;

create table other_fail as
  select *
  from diff_merged
  where notable == 0;

alter table notable_disagree
drop column notable;

alter table other_fail
drop column notable;

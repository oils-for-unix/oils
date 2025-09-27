-- SQL invoked from regtest/aports-html.sh

-- Attach the source databases
attach database 'baseline/tables.db' as baseline;
attach database 'osh-as-sh/tables.db' as osh_as_sh;

-- TODO: rename diff_baseline -> failures
create table diff_baseline as
  select
    b.pkg,
    cast(b.status as integer) as status1,
    b.elapsed_secs as baseline,
    cast("baseline/" || b.pkg_HREF as text) as baseline_HREF,
    cast(o.status as integer) as status2,
    o.elapsed_secs as osh_as_sh,
    cast("osh-as-sh/" || o.pkg_HREF as text) as osh_as_sh_HREF,
    cast("error" as text) as error_grep,
    cast(printf("error/%s.txt", b.pkg) as text) as error_grep_HREF,
    (b.status != o.status) as disagree,
    (b.status in (124, 143) or o.status in (124, 143)) as timeout
  from
    baseline.packages as b
    join osh_as_sh.packages as o on b.pkg = o.pkg
  where b.status != 0 or o.status != 0
  order by b.pkg;

-- Create a table of the right shape
-- 1 row for baseline, 1 row for osh-as-sh
create table metrics as
  select
    cast("baseline" as text) as config,
    *
  from baseline.metrics;

insert into metrics
select
  cast("osh-as-sh" as text) as config,
  *
from osh_as_sh.metrics;

-- Detach databases
detach database baseline;
detach database osh_as_sh;

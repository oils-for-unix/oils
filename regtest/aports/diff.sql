-- SQL invoked from regtest/aports-html.sh

-- Attach the source databases
attach database 'baseline/tables.db' as baseline;
attach database 'osh-as-sh/tables.db' as osh_as_sh;

-- .mode columns
-- select * from packages;

create table diff_baseline as
  select
    b.pkg,
    cast(b.status as integer) as status1,
    cast("baseline" as text) as baseline,
    cast("baseline/" || b.pkg_HREF as text) as baseline_HREF,
    cast(o.status as integer) as status2,
    cast("osh-as-sh" as text) as osh_as_sh,
    cast("osh-as-sh/" || o.pkg_HREF as text) as osh_as_sh_HREF,
    cast("error" as text) as error_grep,
    cast(printf("error/%s.txt", b.pkg) as text) as error_grep_HREF
  from
    baseline.packages as b
    join osh_as_sh.packages as o on b.pkg = o.pkg
  where b.status != o.status
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

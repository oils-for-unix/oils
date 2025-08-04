-- Attach the source databases
attach database 'baseline/tables.db' as baseline;
attach database 'osh-as-sh/tables.db' as osh_as_sh;

-- .mode columns
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
    printf("diff/%s.txt", b.pkg) as diff_HREF,
    "error" as error_grep,
    printf("error/%s.txt", b.pkg) as error_grep_HREF
  from
    baseline.packages as b
    join osh_as_sh.packages as o on b.pkg = o.pkg
  where b.status != o.status
  order by b.pkg;

-- Detach databases
detach database baseline;
detach database osh_as_sh;

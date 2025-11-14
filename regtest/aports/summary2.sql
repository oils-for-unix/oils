-- Side by side table

-- select '<ul>';
-- select printf('<li>Other Failures: %d</li>', count(*)) from other_fail;
-- select
--   printf(
--     '<li>Inconclusive result because of timeout (-124, -143): %d</li>',
--     count(*)
--   )
-- from timeout
-- where cause like 'signal-%';
-- select '</ul>';

-- - Side by-side table

create temporary view summary as
  select
    sum(
      case
        when config = 'baseline' then num_tasks
        else 0
      end
    ) as num_apkbuild,
    sum(
      case
        when config = 'baseline' then num_failures
        else 0
      end
    ) as baseline_failures,
    sum(
      case
        when config = 'osh-as-sh' then num_failures
        else 0
      end
    ) as osh_failures,
    sum(
      case
        when config = 'baseline' then num_timeouts
        else 0
      end
    ) as baseline_timeouts,
    sum(
      case
        when config = 'osh-as-sh' then num_timeouts
        else 0
      end
    ) as osh_timeouts,
    sum(
      case
        when config = 'baseline' then num_apk
        else 0
      end
    ) as baseline_apk,
    sum(
      case
        when config = 'osh-as-sh' then num_apk
        else 0
      end
    ) as osh_apk
  from metrics;

-- Task failures and packages produced

select '<table id="config-summary-table">';
select '<thead>';
select '<tr> <td></td> <td>baseline</td> <td>osh as sh</td> </tr>';
select '</thead>';

-- both sides work from the same APKBUILD
select '<tr> <td> <code>APKBUILD</code> files</td>';
select printf('<td class="num">%d</td>', num_apkbuild) from summary;
select printf('<td class="num">%d</td>', num_apkbuild) from summary;
select '</tr>';

select '<tr> <td> <code>.apk</code> built </td>';
select printf('<td class="num">%d</td>', baseline_apk)
from summary;
select printf('<td class="num">%d</td>', osh_apk)
from summary;
select '</tr>';

select '<tr> <td>Failures</td>';
select
  printf('<td class="num">%d</td>', baseline_failures)
from summary;
select
  printf('<td class="num">%d</td>', osh_failures)
from summary;
select '</tr>';

select '<tr> <td></td>';
select
  printf(
    '<td class="num">(%.1f%%)</td>',
    baseline_failures * 100.0 / num_apkbuild
  )
from summary;

select
  printf('<td class="num">(%.1f%%)</td>', osh_failures * 100.0 / num_apkbuild)
from summary;
select '</tr>';

select '<tr> <td>Timeouts</td>';
select
  printf('<td class="num">%d</td>', baseline_timeouts)
from summary;
select
  printf('<td class="num">%d</td>', osh_timeouts)
from summary;
select '</tr>';

select '<tr> <td></td>';
select
  printf(
    '<td class="num">(%.1f%%)</td>',
    baseline_timeouts * 100.0 / num_apkbuild
  )
from summary;

select
  printf('<td class="num">(%.1f%%)</td>', osh_timeouts * 100.0 / num_apkbuild)
from summary;
select '</tr>';

select '</table>';
-- select '<h2>Common Causes of Disagreements</h2>';

-- select '<table>';
-- select printf('<tr> <td class="num">%d</td> <td>%s</td> <td>%s</td> </tr>', num, cause, cause_HREF)
--   from cause_hist where num > 1;

-- select '</table>';

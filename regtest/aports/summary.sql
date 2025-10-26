select "<ul>";
select printf("<li>Tasks: %d</li>", sum(num_tasks)) from metrics;
select printf("<li><b>Elapsed Hours: %.1f</b></li>", sum(elapsed_minutes) / 60)
from metrics;
select "</ul>";

create temporary view summary as
  select
    sum(
      case
        when config = "baseline" then num_tasks
        else 0
      end
    ) as baseline_tasks,
    sum(
      case
        when config = "baseline" then num_failures
        else 0
      end
    ) as baseline_failures,
    sum(
      case
        when config = "osh-as-sh" then num_failures
        else 0
      end
    ) as osh_failures,
    sum(
      case
        when config = "baseline" then num_apk
        else 0
      end
    ) as baseline_apk,
    sum(
      case
        when config = "osh-as-sh" then num_apk
        else 0
      end
    ) as osh_apk
  from metrics;

-- Task failures and packages produced

select "<ul>";

select printf("<li><code>APKBUILD</code> files: %d</li>", baseline_tasks)
from summary;

select
  printf(
    "<li>Baseline failures: %d (%.1f%%)</li>",
    baseline_failures,
    baseline_failures * 100.0 / baseline_tasks
  )
from summary;

select
  printf(
    "<li>osh-as-sh failures: %d (%.1f%%)</li>",
    osh_failures,
    osh_failures * 100.0 / baseline_tasks
  )
from summary;

select printf("<li>Baseline <code>.apk</code> built: %d</li>", baseline_apk)
from summary;
select printf("<li>osh-as-sh <code>.apk</code> built: %d</li>", osh_apk)
from summary;

select "</ul>";

-- Disagreements

select "<ul>";
select printf("<li><b>Notable Disagreements: %d</b></li>", count(*))
from notable_disagree;

select printf("<li>Unique causes: %d</li>", count(distinct cause))
from notable_disagree
where cause != "unknown";

select
  printf("<li>Packages without a cause assigned (unknown): %s</li>", count(*))
from notable_disagree
where cause = "unknown";
select "</ul>";

-- Other

select "<ul>";
select printf("<li>Other Failures: %d</li>", count(*)) from other_fail;
select
  printf(
    "<li>Inconclusive result because of timeout (-124, -143): %d</li>",
    count(*)
  )
from timeout
where cause like "signal-%";
select "</ul>";

-- SQL invoked from regtest/aports-html.sh

alter table diff_baseline add column cause text;

-- Update diff table with values from causes table
update diff_baseline
set cause = (
  select causes.cause
  from causes
  where causes.pkg = diff_baseline.pkg
);

-- Set causes for signals/timeouts
update diff_baseline
set cause = "signal-124"
where status1 = 124 or status2 = 124;

update diff_baseline
set cause = "signal-143"
where status1 = 143 or status2 = 143;

-- Add Github links (AFTER accounting for signals)
alter table diff_baseline add column cause_HREF text;

update diff_baseline
set cause_HREF = case
  when cause regexp '#[0-9]+' then printf(
    'https://github.com/oils-for-unix/oils/issues/%s',
    ltrim(cause, '#')
  )
  else ''
end;

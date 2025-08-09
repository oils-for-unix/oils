alter table diff add column cause text;

-- Update diff table with values from causes table
update diff
set cause = (
  select causes.cause
  from causes
  where causes.pkg = diff.pkg
);

-- Set causes for signals/timeouts
update diff
set cause = "signal-124"
where status1 = 124 or status2 = 124;

update diff
set cause = "signal-143"
where status1 = 143 or status2 = 143;

-- Add Github links (AFTER accounting for signals)
alter table diff add column cause_HREF text;

update diff
set cause_HREF = case
  when cause regexp '#[0-9]+' then printf(
    'https://github.com/oils-for-unix/oils/issues/%s',
    ltrim(cause, '#')
  )
  else ''
end;

-- For diff.schema.tsv - this snippet copied
create table diff_schema as
  select
    name as column_name,
    case
      when UPPER(type) like "%INT%" then "integer"
      when UPPER(type) = "REAL" then "float"
      when UPPER(type) = "TEXT" then "string"
      else LOWER(type)
    end as type
  from PRAGMA_TABLE_INFO("diff");

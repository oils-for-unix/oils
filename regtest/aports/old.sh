#!/usr/bin/env bash
#
# Old code that might be useful for analysis.
#
# Usage:
#   regtest/aports-old.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

alter-sql() {
  ### unused
    if false; then
      echo '
.mode columns

-- not using this now
ALTER TABLE tasks DROP COLUMN xargs_slot;

-- elapsed is enough; this was for graphing
alter table tasks DROP COLUMN start_time;
alter table tasks DROP COLUMN end_time;

alter table tasks ADD COLUMN user_elapsed_ratio;
update tasks set user_elapsed_ratio = user_secs / elapsed_secs;
alter table tasks DROP COLUMN user_secs;

alter table tasks ADD COLUMN max_rss_MB;
update tasks set max_rss_MB = max_rss_KiB * 1024 / 1e6;
alter table tasks DROP COLUMN max_rss_KiB;
'
  fi
}

# workaround for old VM
# old sqlite doesn't have 'drop column'!
#if sqlite3 --version | grep -q '2018-'; then
if false; then
  sqlite3() {
    ~/src/sqlite-autoconf-3500300/sqlite3 "$@"
  }
fi

log-sizes() {
  local config=${1:-baseline}

  tsv-row 'num_bytes' 'path'
  find $CHROOT_HOME_DIR/oils/_tmp/aports-guest/$config \
    -name '*.log.txt' -a -printf '%s\t%P\n'
}

log-sizes-schema() {
  here-schema-tsv <<EOF
column_name   type   
num_bytes     integer
path          string
EOF
}

big-logs() {
  local config=${1:-baseline}

  local dir=$BASE_DIR/big

  mkdir -p $dir

  concat-task-tsv > $dir/tasks.tsv
  tasks-schema > $dir/tasks.schema.tsv

  log-sizes > $dir/log_sizes.tsv
  log-sizes-schema > $dir/log_sizes.schema.tsv

  { typed-tsv-to-sql $dir/tasks.tsv
    typed-tsv-to-sql $dir/log_sizes.tsv
    echo '.mode table'
    if true; then
    echo 'select * from tasks order by elapsed_secs limit 10;'
    echo 'select * from log_sizes order by num_bytes limit 10;'
    echo 'select elapsed, start_time, end_time from tasks order by elapsed_secs limit 10;'

    echo '
create table big_logs as
select * from log_sizes where num_bytes > 1e6 order by num_bytes;

SELECT "--";

select sum(num_bytes) / 1e6 from log_sizes;

-- this is more than half the logs
select sum(num_bytes) / 1e6 from big_logs;

select * from big_logs;

-- 22 hours, but there was a big pause in the middle
select ( max(end_time)-min(start_time) ) / 60 / 60 from tasks;

-- SELECT status, pkg FROM tasks WHERE status != 0;

-- SELECT * from tasks limit 10;
'
    fi
  } | sqlite3 :memory: 
}

concat-tables() {
  sqlite3 $db <<EOF
-- Attach the source databases
ATTACH DATABASE 'baseline/packages.db' AS baseline;
ATTACH DATABASE 'osh-as-sh/packages.db' AS osh_as_sh;

-- Create the new table by copying the structure and adding config column
-- interesting trick from Claude: where 1 = 0;
-- CREATE TABLE packages AS SELECT 'baseline' AS config, * FROM baseline.packages WHERE 1=0;

-- Insert data from baseline database
-- INSERT INTO packages SELECT 'baseline', * FROM baseline.packages;

-- Insert data from osh-as-sh database
-- INSERT INTO packages SELECT 'osh-as-sh', * FROM osh_as_sh.packages;
EOF
}

diff-report() {
  local dir=$REPORT_DIR/$EPOCH

  { typed-tsv-to-sql $dir/baseline/tasks.tsv baseline
    typed-tsv-to-sql $dir/osh-as-sh/tasks.tsv osh_as_sh
    echo '
.mode column
select count(*) from baseline;
select count(*) from osh_as_sh;
select * from pragma_table_info("baseline");
select * from pragma_table_info("osh_as_sh");

-- 22 hours, but there was a big pause in the middle
select ( max(end_time)-min(start_time) ) / 60 / 60 from baseline;

SELECT status, pkg FROM baseline WHERE status != 0;
'
  }  | sqlite3 :memory:
}


task-five "$@"

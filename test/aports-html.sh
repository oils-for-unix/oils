#!/usr/bin/env bash
#
# Make reports and HTML for test/aports.sh
#
# Usage:
#   test/aports-html.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source test/aports-common.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source test/tsv-lib.sh  # tsv2html3
source web/table/html.sh  # table-sort-{begin,end}
source benchmarks/common.sh  # cmark

html-head() {
  # python3 because we're outside containers
  PYTHONPATH=. python3 doctools/html_head.py "$@"
}

index-html() {
  local base_url='../../web'
  html-head --title "aports Build" \
    "$base_url/base.css"

  # TODO:
  # - Stats for each config:
  #   - number of non-zero exit codes, total packages
  #   - and then links to all the packages that are different
  # And also link to the differences

  # Try sqlite queries
  # Do you add the "config" to each package build?

  cmark <<'EOF'
<body class="width35">

<p id="home-link">
  <a href="/">oils.pub</a>
</p>

# aports Build

Configurations:

- [baseline](baseline/index.html)
- [osh-as-sh](osh-as-sh/index.html)

## Baseline versus osh-as-sh

TODO

## osh-as-sh versus osh-as-bash

TODO

</body>
EOF
}

config-index-html()  {
  local tasks_tsv=$1
  local config=$2

  local base_url='../../../web'
  html-head --title "aports Build: $config" \
    "$base_url/ajax.js" \
    "$base_url/table/table-sort.js" \
    "$base_url/table/table-sort.css" \
    "$base_url/base.css"

  table-sort-begin 'width60'

  cmark <<EOF
<p id="home-link">
  <a href="../index.html">Up</a> |
  <a href="/">Home</a>
</p>

# aports Build: $config
EOF

  tsv2html3 $tasks_tsv

  cmark <<EOF

[tasks.tsv](tasks.tsv)
EOF

  table-sort-end 'tasks'  # ID for sorting
}

readonly BASE_DIR=_tmp/aports-build

concat-task-tsv() {
  local config=${1:-baseline}
  python3 devtools/tsv_concat.py \
    $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp/aports-guest/$config/*.task.tsv
}

log-sizes() {
  local config=${1:-baseline}

  tsv-row 'num_bytes' 'path'
  find $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp/aports-guest/$config \
    -name '*.log.txt' -a -printf '%s\t%P\n'
}

load-sql() {
  local tsv=${1:-$BASE_DIR/big/tasks.tsv}

  local name
  name=$(basename $tsv .tsv)

  local schema="${tsv%'.tsv'}.schema.tsv"
  #echo $name $schema

  echo "CREATE TABLE $name ("
  web/table/schema2sqlite.py $schema
  echo ');'

  echo "
.headers on
.mode tabs

-- have to use this temp import because we already created the table, and 
-- '.headers on' is not expected in that case

.import $tsv temp_import
insert into $name select * from temp_import;
drop table temp_import;

select * from $name limit 5;
  "
}

big-logs() {
  local config=${1:-baseline}

  local dir=$BASE_DIR/big

  mkdir -p $dir

  concat-task-tsv > $dir/tasks.tsv
  tasks-schema > $dir/tasks.schema.tsv

  log-sizes > $dir/log_sizes.tsv
  log-sizes-schema > $dir/log_sizes.schema.tsv

  { load-sql $dir/tasks.tsv
    load-sql $dir/log_sizes.tsv
    echo '.mode table'
    if true; then
    echo 'select * from tasks order by elapsed_secs limit 10;'
    echo 'select * from log_sizes order by num_bytes limit 10;'

    echo '
create table big_logs as
select * from log_sizes where num_bytes > 1e6 order by num_bytes;

SELECT "--";

select sum(num_bytes) / 1e6 from log_sizes;

-- this is more than half the logs
select sum(num_bytes) / 1e6 from big_logs;

select * from big_logs;

-- SELECT status, pkg FROM tasks WHERE status != 0;

-- SELECT * from tasks limit 10;
'
    fi
  } | sqlite3 :memory: 
}

tasks-schema() {
  here-schema-tsv-4col <<EOF
column_name   type      precision strftime
status        integer   0         -
elapsed_secs  float     1         -
user_secs     float     1         -
start_time    float     1         %H:%M:%S
end_time      float     1         %H:%M:%S
sys_secs      float     1         -
max_rss_KiB   integer   0         -
xargs_slot    integer   0         -
pkg           string    0         -
pkg_HREF      string    0         -
EOF
}

log-sizes-schema() {
  here-schema-tsv <<EOF
column_name   type   
num_bytes     integer
path          string
EOF
}

write-report() {
  local config=${1:-baseline}

  local tasks_tsv=$BASE_DIR/$config/tasks.tsv
  mkdir -p $BASE_DIR/$config

  concat-task-tsv "$config" > $tasks_tsv

  cp -v \
    $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp/aports-guest/$config/*.log.txt \
    $BASE_DIR/$config

  log "Wrote $tasks_tsv"

  # TODO: compute these columns
  # - user_secs / elapsed secs - to see how parallel each build is
  # - max_rss_KiB -> max_rss_MB

  tasks-schema >$BASE_DIR/$config/tasks.schema.tsv

  config-index-html $tasks_tsv $config > $BASE_DIR/$config/index.html
  log "Wrote $BASE_DIR/index.html"
}

write-all-reports() {
  index-html > $BASE_DIR/index.html

  for config in baseline osh-as-sh; do
    write-report "$config"
  done
}

show-logs() {
  local config=${1:-baseline}

  #sudo head $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp/aports-guest/main/*.log.txt
  sudo head $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp/aports-guest/$config/*.task.tsv
}

task-five "$@"

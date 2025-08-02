#!/usr/bin/env bash
#
# Make reports and HTML for test/aports.sh
#
# Usage:
#   test/aports-html.sh <function name>
#
# Examples:
#   export EPOCH=2025-07-28-100to300
#   $0 write-all-reports
#   $0 make-wwz
#   $0 deploy-wwz-op    # op.oilshell.org - could be op.oils.pub
#   $0 deploy-wwz-mb    # oils.pub, on Mythic Beasts
#
# TODO:
# - report on start time and end time - on $config/packages.html
#   - lenny machine is a lot slower
# - report on total packages, total failures
# - maybe report the machine name
# - generate a DIFF of the logs!  Make that a new SQL column
#   - start with diff -u

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
  local base_url='../../../web'
  html-head --title "aports Build" \
    "$base_url/base.css"

  # TODO:
  # - Stats for each config:
  #   - number of non-zero exit codes, total packages

  cmark <<'EOF'
<body class="width35">

<p id="home-link">
  <a href="/">oils.pub</a>
</p>

# aports Build

Configurations:

- [baseline](baseline/packages.html) - [raw tasks](baseline/tasks.html) - [metrics](baseline/metrics.txt)
- [osh-as-sh](osh-as-sh/packages.html) - [raw tasks](osh-as-sh/tasks.html) - [metrics](osh-as-sh/metrics.txt)

## Baseline versus osh-as-sh

- [diff-baseline](diff-baseline.html)

## osh-as-sh versus osh-as-bash

TODO

</body>
EOF
}

diff-html() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local name=${2:-diff-baseline}

  local base_url='../../../web'
  html-head --title "Differences" \
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

# Differences

Note: Right now, the diff column is hard to read in many cases.

EOF

  tsv2html3 $base_dir/$name.tsv

  cmark <<EOF

[$name.tsv]($name.tsv)
EOF

  table-sort-end "$name"  # ID for sorting
}

tasks-html()  {
  local tsv=$1
  # note: escaping problems with title
  # it gets interpolated into markdown and html
  local title=$2

  local base_url='../../../../web'
  html-head --title "$title" \
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

# $title
EOF

  tsv2html3 $tsv

  local id=$(basename $tsv .tsv)
  cmark <<EOF

[$id.tsv]($id.tsv)
EOF

  table-sort-end "$id"  # ID for sorting
}

typed-tsv-to-sql() {
  local tsv=${1:-$BASE_DIR/big/tasks.tsv}
  local name
  name=${2:-$(basename $tsv .tsv)}

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

-- select * from $name limit 5;
  "
}

my-rsync() {
  #rsync --archive --verbose --dry-run "$@"
  rsync --archive --verbose "$@"
}

readonly EPOCH=${EPOCH:-'2025-07-28-100'}
readonly HOST_BASELINE=he.oils.pub
readonly HOST_SH=he.oils.pub
#readonly HOST_SH=lenny.local

sync-results() {
  local dest=$REPORT_DIR/$EPOCH

  mkdir -p $dest

  my-rsync \
    $HOST_BASELINE:~/git/oils-for-unix/oils/_tmp/aports-build/baseline/ \
    $dest/baseline/

  my-rsync \
    $HOST_SH:~/git/oils-for-unix/oils/_tmp/aports-build/osh-as-sh/ \
    $dest/osh-as-sh/
}

make-package-table() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local config=${2:-baseline}

  local db=$base_dir/$config/tables.db
  rm -f $db

  typed-tsv-to-sql $base_dir/$config/tasks.tsv | sqlite3 $db

  sqlite3 -cmd '.mode columns' $db < test/aports-tasks.sql

  sqlite3 $db >$base_dir/$config/packages.tsv <<'EOF'
.mode tabs
.headers on
select * from packages;
EOF

  sqlite3 $db >$base_dir/$config/packages.schema.tsv <<'EOF'
.mode tabs
.headers on
select * from packages_schema;
EOF

  sqlite3 $db >$base_dir/$config/metrics.txt <<EOF
.mode column
select * from metrics;
EOF

  #cat $base_dir/$config/packages.schema.tsv 
}

tasks-schema() {
  here-schema-tsv-4col <<EOF
column_name   type      precision strftime
status        integer   0         -
elapsed_secs  float     1         -
start_time    float     1         %H:%M:%S
end_time      float     1         %H:%M:%S
user_secs     float     1         -
sys_secs      float     1         -
max_rss_KiB   integer   0         -
xargs_slot    integer   0         -
pkg           string    0         -
pkg_HREF      string    0         -
EOF
}

write-tables-for-config() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local config=${2:-baseline}

  local tasks_tsv=$base_dir/$config/tasks.tsv
  mkdir -p $base_dir/$config

  tasks-schema >$base_dir/$config/tasks.schema.tsv

  local out=$base_dir/$config/tasks.html
  tasks-html $tasks_tsv "tasks: $config" > $out
  log "Wrote $out"

  make-package-table "$base_dir" "$config"

  local packages_tsv=$base_dir/$config/packages.tsv

  local out=$base_dir/$config/packages.html
  tasks-html $packages_tsv "packages: $config" > $out
  log "Wrote $out"
}

make-diff-db() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local name=${2:-diff-baseline}

  local db=$name.db

  local sql=$PWD/test/aports-diff.sql

  pushd $base_dir
  rm -f $db
  sqlite3 $db < $sql

  sqlite3 $db >$name.tsv <<EOF
.mode tabs
.headers on
select * from diff;
EOF

  sqlite3 $db >$name.schema.tsv <<EOF
.mode tabs
.headers on
select * from diff_schema;
EOF

  #
  # Now make diffs
  #

  sqlite3 $db >packages-to-diff.txt <<EOF
.mode tabs
.headers off
select pkg from diff;
EOF

  mkdir -p diff error
  cat packages-to-diff.txt | while read -r pkg; do
    local left=baseline/log/$pkg.log.txt 
    local right=osh-as-sh/log/$pkg.log.txt 
    diff -u $left $right > diff/$pkg.txt || true
    egrep -i 'error' $right > error/$pkg.txt || true
  done

  #cat $name.schema.tsv 

  popd
}

write-all-reports() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}

  index-html > $base_dir/index.html

  for config in baseline osh-as-sh; do
    write-tables-for-config "$base_dir" "$config"
  done

  local name=diff-baseline
  make-diff-db
  diff-html $base_dir > $base_dir/$name.html
  echo "Wrote $base_dir/$name.html"
}

make-wwz() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local wwz=$REPORT_DIR/$EPOCH.wwz 
  zip -r $wwz $base_dir web/
}

deploy-wwz-op() {
  #local host=op.oilshell.org 
  local host=op.oils.pub

  #ssh $host ls op.oilshell.org/

  local dest_dir=$host/aports-build
  ssh $host mkdir -p $dest_dir
  scp $REPORT_DIR/$EPOCH.wwz $host:$dest_dir

  echo "Visit https://$dest_dir/$EPOCH.wwz/"
}

deploy-wwz-mb() {
  local host=oils.pub

  #ssh $host ls op.oilshell.org/

  local dest_dir=www/$host/aports-build
  ssh $host mkdir -p $dest_dir
  scp $REPORT_DIR/$EPOCH.wwz $host:$dest_dir
}

out-of-vm() {
  local dest=~/vm-shared/$EPOCH
  mkdir -p $dest
  cp $REPORT_DIR/$EPOCH.wwz $dest
  pushd ~/vm-shared/$EPOCH
  unzip $EPOCH.wwz
  popd
}

task-five "$@"

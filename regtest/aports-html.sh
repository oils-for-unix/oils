#!/usr/bin/env bash
#
# Make reports and HTML for regtest/aports.sh
#
# Usage:
#   regtest/aports-html.sh <function name>
#
# Examples:
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

source regtest/aports-common.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source test/tsv-lib.sh  # tsv2html3
source web/table/html.sh  # table-sort-{begin,end}
source benchmarks/common.sh  # cmark

html-head() {
  # python3 because we're outside containers
  PYTHONPATH=. python3 doctools/html_head.py "$@"
}

index-html() {
  local base_url='../../../../web'
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

diff-metrics-html() {
  local db=${1:-_tmp/aports-report/2025-08-03/diff-joined.db}

  echo '<ul>'
  sqlite3 $db <<EOF
-- select printf("<li>Shards: %s</li>", count(distinct shard)) from diff_joined;
select printf("<li>Differences: %s</li>", count(*)) from diff_joined;
select printf("<li>Unique causes: %s</li>", count(distinct cause)) from diff_joined where cause >= 0;
select printf("<li>Packages without a cause assigned (-200): %s</li>", count(*)) from diff_joined where cause = "-200";
select printf("<li>Inconclusive result because of timeout (-124): %s</li>", count(*)) from diff_joined where cause = "-124";
EOF
  echo '</ul>'
}

diff-html() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local name=${2:-diff-baseline}
  local base_url=${3:-'../../../../web'}

  local title='Differences - OSH'

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

  if test "$name" = 'diff-joined'; then
    diff-metrics-html $base_dir/$name.db
  fi

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

  local base_url='../../../../../web'
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
readonly BUILD_HOST=he.oils.pub
#readonly BUILD_HOST=lenny.local

sync-results() {
  local host=${1:-$BUILD_HOST}
  mkdir -p $REPORT_DIR

  my-rsync \
    $host:~/git/oils-for-unix/oils/_tmp/aports-build/ \
    $REPORT_DIR/

  return

  # OLD
  my-rsync \
    $HOST_BASELINE:~/git/oils-for-unix/oils/_tmp/aports-build/baseline/ \
    $dest/baseline/

  my-rsync \
    $HOST_SH:~/git/oils-for-unix/oils/_tmp/aports-build/osh-as-sh/ \
    $dest/osh-as-sh/
}

local-sync() {
  mkdir -p $REPORT_DIR

  #my-rsync --dry-run $BASE_DIR/ $REPORT_DIR/
  my-rsync $BASE_DIR/ $REPORT_DIR/
}

make-package-table() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local config=${2:-baseline}

  local db=$base_dir/$config/tables.db
  rm -f $db

  typed-tsv-to-sql $base_dir/$config/tasks.tsv | sqlite3 $db

  sqlite3 -cmd '.mode columns' $db < regtest/aports-tasks.sql

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
  local base_dir=$1
  local name=${2:-diff-baseline}

  local db=$name.db

  local diff_sql=$PWD/regtest/aports-diff.sql
  local cause_awk=$PWD/regtest/aports-cause.awk

  pushd $base_dir
  rm -f $db
  sqlite3 $db < $diff_sql

  #
  # Now make diffs
  #

  sqlite3 $db >failed-packages.txt <<EOF
.mode tabs
.headers off
select pkg from diff;
EOF

  mkdir -p error
  cat failed-packages.txt | while read -r pkg; do
    local left=baseline/log/$pkg.log.txt 
    local right=osh-as-sh/log/$pkg.log.txt 

    egrep -i 'error|fail' $right > error/$pkg.txt || true
  done

  { echo "pkg${TAB}cause"
    cat failed-packages.txt | while read -r pkg; do
      local right=osh-as-sh/log/$pkg.log.txt 

      local cause
      cause=$(awk -f $cause_awk $right)

      echo "${pkg}${TAB}${cause}"
    done 
  } > causes.tsv

  sqlite3 $db <<EOF
.mode tabs
.headers on
.import causes.tsv causes

ALTER TABLE diff ADD COLUMN cause INT;

-- Update with values from causes table
UPDATE diff
SET cause = (
    SELECT causes.cause
    FROM causes
    WHERE causes.pkg = diff.pkg
);

-- Now set for timeouts
UPDATE diff
SET cause = -124
WHERE status1 = 124 OR status2 = 124;

EOF

  sqlite3 $db >$name.tsv <<EOF
.mode tabs
.headers on
select * from diff;
EOF

  sqlite3 $db >$name.schema.tsv <<EOF
-- This snippet copied
create table diff_schema as
  select
    name as column_name,
    case
      when UPPER(type) LIKE "%INT%" then "integer"
      when UPPER(type) = "REAL" then "float"
      when UPPER(type) = "TEXT" then "string"
      else LOWER(type)
    end as type
  from PRAGMA_TABLE_INFO("diff");

.mode tabs
.headers on
select * from diff_schema;
EOF

  popd
}

join-diffs-sql() {
  local -a SHARDS=( "$@" )

  local first_shard="${SHARDS[0]}"

  local shard_name
  shard_name=$(basename $first_shard)

  # Create table from first shard
  echo "
  ATTACH DATABASE '$first_shard/diff-baseline.db' AS temp_shard;
  CREATE TABLE diff_joined AS
  SELECT *, CAST('' as TEXT) as shard FROM temp_shard.diff where 1=0;
  DETACH DATABASE temp_shard;
  "

  # Now insert data from all the shards
  for ((i=0; i<${#SHARDS[@]}; i++)); do
    local shard_db="${SHARDS[i]}"
    shard_name=$(basename $shard_db)
      
    echo "
    -- $i: Add data from $shard_db
    ATTACH DATABASE '$shard_db/diff-baseline.db' AS temp_shard;
    INSERT INTO diff_joined
    SELECT *, '$shard_name' as shard FROM temp_shard.diff;
    DETACH DATABASE temp_shard;
    "
  done

  echo '
UPDATE diff_joined SET
   baseline_HREF = printf("%s/%s", shard, baseline_HREF),
   osh_as_sh_HREF = printf("%s/%s", shard, osh_as_sh_HREF),
   error_grep_HREF = printf("%s/%s", shard, error_grep_HREF);
  
-- Useful queries to verify the result:
-- SELECT COUNT(*) as total_rows FROM diff_joined;
-- SELECT shard, COUNT(*) as row_count FROM diff_joined GROUP BY shard ORDER BY shard;
-- .schema diff_joined

-- copied

create table diff_joined_schema as
  select
    name as column_name,
    case
      when UPPER(type) LIKE "%INT%" then "integer"
      when UPPER(type) = "REAL" then "float"
      when UPPER(type) = "TEXT" then "string"
      else LOWER(type)
    end as type
  from PRAGMA_TABLE_INFO("diff_joined");
'
}

join-diffs() {
  local epoch_dir=${1:-_tmp/aports-report/2025-08-03}
  local db=$PWD/$epoch_dir/diff-joined.db
  rm -f $db
  join-diffs-sql $epoch_dir/shard* | sqlite3 $db
  echo $db

  local name=diff-joined

  # copied from above
  pushd $epoch_dir

  sqlite3 $db >$name.tsv <<EOF
.mode tabs
.headers on
select * from diff_joined order by pkg;
EOF

  sqlite3 $db >$name.schema.tsv <<EOF
.mode tabs
.headers on
select * from diff_joined_schema;
EOF
  popd

  local out=$epoch_dir/$name.html
  diff-html $epoch_dir $name '../../../web' > $out
  echo "Wrote $out"
}

write-shard-reports() {
  local base_dir=$1  # e.g. _tmp/aports-report/2025-08-02/shard3

  index-html > $base_dir/index.html

  for config in baseline osh-as-sh; do
    write-tables-for-config "$base_dir" "$config"
  done

  local name=diff-baseline
  make-diff-db $base_dir
  diff-html $base_dir > $base_dir/$name.html
  echo "Wrote $base_dir/$name.html"
}

write-all-reports() {
  local epoch_dir=${1:-_tmp/aports-report/2025-08-03}
  for shard_dir in $epoch_dir/shard*; do
    write-shard-reports "$shard_dir"
  done

  join-diffs "$epoch_dir"
}

make-wwz() {
  local base_dir=${1:-$REPORT_DIR/2025-08-03}

  # must not end with slash
  local wwz=$base_dir.wwz

  zip -r $wwz $base_dir web/
}

deploy-wwz-op() {
  local wwz=${1:-$REPORT_DIR/2025-08-03.wwz}

  local host=op.oils.pub

  #local host=op.oilshell.org 

  local dest_dir=$host/aports-build
  ssh $host mkdir -p $dest_dir
  scp $wwz $host:$dest_dir

  echo "Visit https://$dest_dir/$(basename $wwz)/"
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

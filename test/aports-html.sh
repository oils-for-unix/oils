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

- [baseline](baseline/packages.html) - [raw tasks](baseline/tasks.html)
- [osh-as-sh](osh-as-sh/packages.html) - [raw tasks](osh-as-sh/tasks.html)

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

  local db=$base_dir/$config/packages.db
  rm -f $db

  { typed-tsv-to-sql $base_dir/$config/tasks.tsv
   echo '
.mode columns

-- select * from tasks limit 5;

-- annoying: you have to cast(x as real) for pragma_info to have type info
create table packages as
select status, 
       elapsed_secs,
       cast( user_secs / elapsed_secs as real) as user_elapsed_ratio,
       cast( user_secs / sys_secs as real) as user_sys_ratio,
       cast(max_rss_KiB * 1024 / 1e6 as real) as max_rss_MB,
       pkg, 
       pkg_HREF
from tasks;

-- sqlite table schema -> foo.schema.tsv
CREATE TABLE packages_schema AS
SELECT 
    name AS column_name,
    CASE 
        WHEN UPPER(type) = "INTEGER" THEN "integer"
        WHEN UPPER(type) = "REAL" THEN "float"
        WHEN UPPER(type) = "TEXT" THEN "string"
        ELSE LOWER(type)
    END AS type
FROM PRAGMA_TABLE_INFO("packages");

-- select * from packages_schema;

alter table packages_schema add column precision;

update packages_schema SET precision = 1 where column_name = "elapsed_secs";
update packages_schema SET precision = 1 where column_name = "user_elapsed_ratio";
update packages_schema SET precision = 1 where column_name = "user_sys_ratio";
update packages_schema SET precision = 1 where column_name = "max_rss_MB";
'
  } | sqlite3 $db

  sqlite3 $db >$base_dir/$config/packages.tsv <<EOF
.mode tabs
.headers on
select * from packages;
EOF

  sqlite3 $db >$base_dir/$config/packages.schema.tsv <<EOF
.mode tabs
.headers on
select * from packages_schema;
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

  pushd $base_dir
  rm -f $db
  sqlite3 $db <<EOF
-- Attach the source databases
ATTACH DATABASE 'baseline/packages.db' AS baseline;
ATTACH DATABASE 'osh-as-sh/packages.db' AS osh_as_sh;

.mode columns
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
  printf("error/%s.txt", b.pkg) as diff_HREF,
  "error" as error_grep,
  printf("error/%s.txt", b.pkg) as error_grep_HREF
from baseline.packages b
join osh_as_sh.packages o on b.pkg = o.pkg
where b.status != o.status
order by b.pkg;

-- Copied from above
CREATE TABLE diff_schema AS
SELECT 
    name AS column_name,
    CASE 
        WHEN UPPER(type) = "INTEGER" THEN "integer"
        WHEN UPPER(type) = "REAL" THEN "float"
        WHEN UPPER(type) = "TEXT" THEN "string"
        ELSE LOWER(type)
    END AS type
FROM PRAGMA_TABLE_INFO("diff");

-- Detach databases
DETACH DATABASE baseline;
DETACH DATABASE osh_as_sh;
EOF

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

#!/usr/bin/env bash
#
# Make HTML reports
#
# Usage:
#   regtest/aports-html.sh <function name>
#
# Examples:
#   $0 sync-results he.oils.pub
#   $0 write-all-reports
#   $0 make-wwz _tmp/aports-report/2025-08-03
#   $0 deploy-wwz-op _tmp/aports-report/2025-08-03.wwz   # deploy to op.oils.pub

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source test/tsv-lib.sh  # tsv2html3
source web/table/html.sh  # table-sort-{begin,end}
source benchmarks/common.sh  # cmark

sqlite-tabs-headers() {
  sqlite3 \
    -cmd '.mode tabs' \
    -cmd '.headers on' \
    "$@"
}

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
  <a href="/">Home</a>
</p>

# aports Build

Configurations:

- [baseline](baseline/packages.html) - [raw tasks](baseline/tasks.html) - [metrics](baseline/metrics.txt)
- [osh-as-sh](osh-as-sh/packages.html) - [raw tasks](osh-as-sh/tasks.html) - [metrics](osh-as-sh/metrics.txt)

## Baseline versus osh-as-sh

- [diff_baseline](diff_baseline.html)

## osh-as-sh versus osh-as-bash

TODO

</body>
EOF
}

diff-metrics-html() {
  local db=${1:-_tmp/aports-report/2025-08-03/diff_merged.db}

  sqlite3 $db <<EOF
-- this is only shards with disagreements; we want total shards
-- select printf("<li>Shards: %s</li>", count(distinct shard)) from diff_merged;
-- select printf("<li><code>.apk</code> packages produced: %s</li>", count(distinct apk_name)) from apk_merged;

select "<ul>";
select printf("<li>Tasks: %s</li>", sum(num_tasks)) from metrics;
select printf("<li>Elapsed Hours: %.1f</li>", sum(elapsed_minutes) / 60) from metrics;
select "</ul>";

select "<ul>";
select printf("<li>Baseline <code>.apk</code> built: %s</li>", sum(num_apk)) from metrics where config = "baseline";
select printf("<li>osh-as-sh <code>.apk</code> built: %s</li>", sum(num_apk)) from metrics where config = "osh-as-sh";
select printf("<li>Baseline failures: %s</li>", sum(num_failures)) from metrics where config = "baseline";
select printf("<li>osh-as-sh failures: %s</li>", sum(num_failures)) from metrics where config = "osh-as-sh";
select "</ul>";

select "<ul>";
select printf("<li>Disagreements: %s</li>", count(*)) from diff_merged;
select printf("<li>Unique causes: %s</li>", count(distinct cause)) from diff_merged where cause >= 0;
select printf("<li>Packages without a cause assigned (unknown): %s</li>", count(*)) from diff_merged where cause = "unknown";
select printf("<li>Inconclusive result because of timeout (-124, -143): %s</li>", count(*)) from diff_merged where cause like "timeout-%";
select "</ul>";
EOF
}

diff-html() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local name=${2:-diff_baseline}
  local base_url=${3:-'../../../../web'}

  local title='OSH Disagreements - regtest/aports'

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

  if test "$name" = 'diff_merged'; then
    diff-metrics-html $base_dir/$name.db
    cmark <<< '[tree](tree.html) &nbsp;&nbsp; [metrics](metrics.html)'
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

published-html() {
  local base_url='../../web'

  local title='regtest/aports'

  html-head --title "$title" \
    "$base_url/base.css"

  echo '
  <body class="width35">
    <style>
      code { color: green; }
    </style>

    <p id="home-link">
      <a href="/">Home</a> |
      <a href="https://oils.pub/">oils.pub</a>
    </p>
  '

  cmark <<EOF
## $title

- [2025-08-07-fix](2025-08-07-fix.wwz/_tmp/aports-report/2025-08-07-fix/diff_merged.html)
- [2025-08-14-fix](2025-08-14-fix.wwz/_tmp/aports-report/2025-08-14-fix/diff_merged.html)
- [2025-08-26-ifs](2025-08-26-ifs.wwz/_tmp/aports-report/2025-08-26-ifs/diff_merged.html)
  - new causes: [2025-09-06-edit](2025-09-06-edit.wwz/_tmp/aports-report/2025-09-06-edit/diff_merged.html)

EOF

  echo '
  </body>
</html>
'
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
-- use this temp import because we already created the table, and 
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

  # Exclude .apk files, because they are large.  We only need the metadata
  my-rsync \
    --exclude '*.apk' \
    $host:~/git/oils-for-unix/oils/_tmp/aports-build/ \
    $REPORT_DIR/
}

local-sync() {
  mkdir -p $REPORT_DIR

  #my-rsync --dry-run $BASE_DIR/ $REPORT_DIR/
  my-rsync $BASE_DIR/ $REPORT_DIR/
}

make-package-table() {
  local base_dir=${1:-$REPORT_DIR/$EPOCH}
  local config=${2:-baseline}

  local db=$PWD/$base_dir/$config/tables.db
  rm -f $db

  typed-tsv-to-sql $base_dir/$config/tasks.tsv | sqlite-tabs-headers $db

  sqlite3 -cmd '.mode columns' $db < regtest/aports/tasks.sql

  pushd $base_dir/$config > /dev/null

  db-to-tsv $db packages

  # Set precision
  echo "
  alter table packages_schema add column precision;
  
  update packages_schema set precision = 1 where column_name = 'elapsed_secs';
  update packages_schema set precision = 1 where column_name = 'user_elapsed_ratio';
  update packages_schema set precision = 1 where column_name = 'user_sys_ratio';
  update packages_schema set precision = 1 where column_name = 'max_rss_MB';
  " | sqlite3 $db

  # Count .apk for this config
  # Note: we could also create an 'apk' table, in addition to 'packages', and diff
  # But that's a bunch of overhead

  if true; then  # backfill for 2025-09-07 run, can delete afterward
    for name in apk/*.apk; do
      echo $name
    done > apk.txt
  fi

  local num_apk
  num_apk=$(cat apk.txt | wc -l)

  sqlite3 $db >metrics.txt <<EOF
update metrics
set num_apk = $num_apk
where id = 1;

.mode column
select * from metrics;
EOF

  popd > /dev/null

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
  local name=${2:-diff_baseline}

  local db=$name.db

  local diff_sql=$PWD/regtest/aports/diff.sql
  local cause_awk=$PWD/regtest/aports/cause.awk
  local cause_sql=$PWD/regtest/aports/cause.sql

  pushd $base_dir > /dev/null

  rm -f $db
  sqlite3 $db < $diff_sql

  #
  # Now make diffs
  #

  sqlite3 $db >failed-packages.txt <<EOF
.mode tabs
-- this is a text file, so headers are OFF
.headers off

select pkg from diff_baseline;
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

  # Import causes.tsv and add columns
  sqlite-tabs-headers \
    -cmd '.import causes.tsv causes' \
    $db < $cause_sql

  # The DB is diff_baseline.db, with table diff_baseline
  db-to-tsv $db diff_baseline

  popd > /dev/null
}

db-to-tsv() {
  local db=$1
  local table_name=$2
  local order_by=${3:-}

  echo "
  select * from ${table_name} ${order_by};
  " | sqlite-tabs-headers $db >$table_name.tsv

  echo "
  create table ${table_name}_schema as
    select
      name as column_name,
      case
        when UPPER(type) like '%INT%' then 'integer'
        when UPPER(type) = 'REAL' then 'float'
        when UPPER(type) = 'TEXT' then 'string'
        else LOWER(type)
      end as type
    from PRAGMA_TABLE_INFO('${table_name}');

  select * from ${table_name}_schema;
  " | sqlite-tabs-headers $db >$table_name.schema.tsv
}

merge-diffs-sql() {
  local -a SHARDS=( "$@" )

  local first_shard="${SHARDS[0]}"

  local shard_name
  shard_name=$(basename $first_shard)

  # Create table from first shard
  echo "
  ATTACH DATABASE '$first_shard/diff_baseline.db' AS temp_shard;

  CREATE TABLE diff_merged AS
  SELECT *, CAST('' as TEXT) as shard FROM temp_shard.diff_baseline where 1=0;

  CREATE TABLE metrics AS
  SELECT *, CAST('' as TEXT) as shard FROM temp_shard.metrics where 1=0;

  DETACH DATABASE temp_shard;
  "

  # Now insert data from all the shards
  for ((i=0; i<${#SHARDS[@]}; i++)); do
    local shard_dir="${SHARDS[i]}"
    shard_name=$(basename $shard_dir)

    # Handle incomplete shard
    if ! test -d $shard_dir/baseline || ! test -d $shard_dir/osh-as-sh; then
      continue
    fi
      
    echo "
    -- $i: Add data from $shard_dir
    ATTACH DATABASE '$shard_dir/diff_baseline.db' AS temp_shard;

    INSERT INTO diff_merged
    SELECT *, '$shard_name' as shard FROM temp_shard.diff_baseline;

    INSERT INTO metrics
    SELECT *, '$shard_name' as shard FROM temp_shard.metrics;

    DETACH DATABASE temp_shard;
    "
  done

  # Does not involve metaprogramming
  cat regtest/aports/merge.sql
}

make-apk-merged() {
  local epoch_dir=${1:-_tmp/aports-report/2025-08-12-ten}
  local db=${2:-$epoch_dir/diff_merged.db}

  # this is a TSV file with no header
  cat $epoch_dir/*/apk-list.txt > apk-merged.txt

  sqlite3 $db << 'EOF'
.mode tabs
.headers off

drop table if exists apk_merged;

create table apk_merged (
  num_bytes integer,
  apk_name
);

.import apk-merged.txt apk_merged

-- queries for later
-- select count(*) from apk_merged;
-- select count(distinct apk_name) from apk_merged;

-- select * from PRAGMA_TABLE_INFO("apk_merged");

.mode columns
.headers on
-- select * from apk_merged limit 10;

EOF
}


merge-diffs() {
  local epoch_dir=${1:-_tmp/aports-report/2025-08-03}
  local db=$PWD/$epoch_dir/diff_merged.db
  rm -f $db
  # TODO: may fail on incomplete shard
  merge-diffs-sql $epoch_dir/shard* | sqlite3 $db
  echo $db

  local name1=diff_merged
  local name2=metrics

  # copied from above
  pushd $epoch_dir > /dev/null

  db-to-tsv $db diff_merged 'order by pkg'
  db-to-tsv $db metrics

  popd > /dev/null

  #make-apk-merged $epoch_dir $db

  local out=$epoch_dir/$name1.html
  diff-html $epoch_dir $name1 '../../../web' > $out
  echo "Wrote $out"

  local out=$epoch_dir/$name2.html
  diff-html $epoch_dir $name2 '../../../web' > $out
  echo "Wrote $out"

  # After merging, regenerate other stuff too

  html-tree "$epoch_dir"

  update-published  # also done in deploy-published
}

write-shard-reports() {
  local base_dir=$1  # e.g. _tmp/aports-report/2025-08-02/shard3

  index-html > $base_dir/index.html

  for config in baseline osh-as-sh; do
    # Incomplete shard
    if ! test -d "$base_dir/$config"; then
      return
    fi
    write-tables-for-config "$base_dir" "$config"
  done

  local name=diff_baseline
  make-diff-db $base_dir
  diff-html $base_dir > $base_dir/$name.html
  echo "Wrote $base_dir/$name.html"
}

write-all-reports() {
  local epoch_dir=${1:-_tmp/aports-report/2025-08-03}
  for shard_dir in $epoch_dir/shard*; do
    write-shard-reports "$shard_dir"
  done

  merge-diffs "$epoch_dir"
}

html-tree() {
  local epoch_dir=${1:-_tmp/aports-report/2025-08-07-fix}

  local epoch
  epoch=$(basename $epoch_dir)

  pushd $epoch_dir
  # -L 3 goes 3 levels deeps, omitting logs
  tree \
    -H './' \
    -T "regtest/aports - $epoch" \
    -L 3 \
    --charset=ascii \
    > tree.html
  popd

  echo "Wrote $epoch_dir/tree.html"
}

update-published() {
  local out=$REPORT_DIR/published.html
  published-html > $out
  echo "Wrote $out"
}

make-wwz() {
  local base_dir=${1:-$REPORT_DIR/2025-08-03}

  # must not end with slash
  base_dir=${base_dir%'/'}

  local wwz=$base_dir.wwz
  rm -f -v $wwz

  zip -r $wwz $base_dir web/

  echo "Wrote $wwz"
}

readonly WEB_HOST=op.oils.pub

deploy-wwz-op() {
  local wwz=${1:-$REPORT_DIR/2025-08-03.wwz}

  local dest_dir=$WEB_HOST/aports-build

  update-published  # slightly redundant

  ssh $WEB_HOST mkdir -p $dest_dir

  scp $wwz $REPORT_DIR/published.html \
    $WEB_HOST:$dest_dir/

  echo "Visit https://$dest_dir/published.html"
  echo "      https://$dest_dir/$(basename $wwz)/"
}

deploy-published() {
  local dest_dir=$WEB_HOST/aports-build

  update-published  # slightly redundant

  scp $REPORT_DIR/published.html \
    $WEB_HOST:$dest_dir/

  echo "Visit https://$dest_dir/published.html"
}

#
# For editing
#

readonly EDIT_DIR=_tmp/aports-edit

sync-wwz() {
  local wwz=${1:-2025-08-26-ifs.wwz}

  mkdir -p $EDIT_DIR

  rsync --archive --verbose \
    $WEB_HOST:$WEB_HOST/aports-build/$wwz  \
    $EDIT_DIR/$wwz

  ls -l $EDIT_DIR
  #echo "Wrote $wwz"
}

extract() {
  local wwz=${1:-2025-08-26-ifs.wwz}
  local new_epoch=${2:-2025-09-06-edit}

  # Extract the whole thing into a temp dir
  local tmp_dir=$EDIT_DIR/$new_epoch
  rm -r -f $tmp_dir
  mkdir -p $tmp_dir

  pushd $tmp_dir
  unzip ../$wwz
  popd

  # Now re-create the old structure under _tmp/aports-report/2025-09-06-edit

  local dest_dir=$REPORT_DIR/$new_epoch
  mkdir -p $dest_dir

  local old_epoch
  old_epoch=$(basename $wwz .wwz)
  mv -v --no-target-directory $tmp_dir/_tmp/aports-report/$old_epoch $dest_dir
}

#
# Dev tools
#

out-of-vm() {
  local dest=~/vm-shared/$EPOCH
  mkdir -p $dest
  cp $REPORT_DIR/$EPOCH.wwz $dest
  pushd ~/vm-shared/$EPOCH
  unzip $EPOCH.wwz
  popd
}

task-five "$@"

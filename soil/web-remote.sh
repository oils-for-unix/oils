#!/usr/bin/env bash
#
# Functions to invoke soil/web remotely.
# 
# soil/web is deployed manually, and then this runs at HEAD in the repo.
# Every CI run has an up-to-date copy.
#
# Usage:
#   source soil/web-remote.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source soil/common.sh

# ~/
#   soil-web/
#    doctools/
#      html_head.py
#    soil/
#      web.py
#      web.sh
#   travis-ci.oilshell.org/
#     index.html
#     web/
#       base.css
#       soil.css
#     jobs/
#       index.html   # rewritten on every job
#       1581.1.wwz   # build 1581 has multiple jobs
#       1581.2.wwz
#       1581.3.wwz
#     builds/
#       src/
#         oil-48ab99c.tar.xz  # named after commits?  Or jobs?
#         oil-58a669c.tar.xz
#       x86_64_musl/   # binaries
#         linux

sshq() {
  # Don't need commands module as I said here!
  # http://www.oilshell.org/blog/2017/01/31.html
  #
  # This is Bernstein chaining through ssh.

  ssh $SOIL_USER@$SOIL_HOST "$(printf '%q ' "$@")"
}

remote-rewrite-jobs-index() {
  local prefix=$1
  sshq soil-web/soil/web.sh rewrite-jobs-index "$prefix"
}

remote-cleanup-jobs-index() {
  local prefix=$1
  # clean it up for real!
  sshq soil-web/soil/web.sh cleanup-jobs-index "$prefix" false
}

remote-cleanup-status-api() {
  sshq soil-web/soil/web.sh cleanup-status-api false
}

scp-results() {
  # could also use Travis known_hosts addon?
  local prefix=$1  # srht- or ''
  shift

  scp -o StrictHostKeyChecking=no "$@" \
    "$SOIL_USER_HOST:travis-ci.oilshell.org/${prefix}jobs/"
}

scp-status-api() {
  local run_id=${1:-TEST2-github-run-id}
  local job_name=$2
  local file=$3

  local remote_path="travis-ci.oilshell.org/status-api/github/$run_id/$job_name"

  ssh -o StrictHostKeyChecking=no \
    $SOIL_USER_HOST "mkdir -p $(dirname $remote_path)"

  # the consumer should check if these are all zero
  # note: the file gets RENAMED
  scp -o StrictHostKeyChecking=no $file \
    "$SOIL_USER_HOST:$remote_path"
}

list-remote-results() {
  local prefix=$1
  ssh -o StrictHostKeyChecking=no \
    $SOIL_USER_HOST ls "travis-ci.oilshell.org/${prefix}jobs/"
}

# Dummy that doesn't depend on results
deploy-test-wwz() {
  set -x
  local out_name="$(date +%Y-%m-%d__%H-%M-%S)_test"

  local wwz=$out_name.wwz

  cat >index.html <<EOF
<a href="build/oil-manifest.txt">build/oil-manifest.txt</a> <br/>
<a href="build/opy-manifest.txt">build/opy-manifest.txt</a> <br/>
<a href="env.txt">env.txt</a> <br/>
EOF

  dump-env > env.txt

  zip -q $wwz env.txt index.html build/*.txt

  scp-results '' $wwz
}

format-wwz-index() {
  ### What's displayed in $ID.wwz/index.html

  local job_id=$1
  local tsv=${2:-_tmp/soil/INDEX.tsv}

  soil-html-head "CI job $job_id"

  cat <<EOF
  <body class="width40">
    <p id="home-link">
        <a href="..">Up</a>
      | <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>CI job <code>$job_id</code></h1>

    <table>
      <thead>
        <tr>
          <td>Task</td>
          <td>Elapsed</td>
          <td>Status</td>
          <td>Details</td>
        </tr>
      </thead>
EOF
  cat $tsv | while read status elapsed task script action result_html; do
    echo "<tr>"
    echo "  <td>
               <a href=\"_tmp/soil/logs/$task.txt\">$task</a> <br/>
               <code>$script $action</code>
            </td>
         "

    printf -v elapsed_str '%.2f' $elapsed
    echo "  <td>$elapsed_str</td>"

    case $status in
      (0)  # exit code 0 is success
        echo "  <td>$status</td>"
        ;;
      (*)  # everything else is a failure
        # Add extra text to make red stand out.
        echo "  <td class=\"fail\">status: $status</td>"
        ;;
    esac

    case $result_html in
      (-)
        echo "  <td>-</td>"
        ;;
      (*)
        echo "  <td><a href=$result_html>Results</a></td>"
        ;;
    esac

    echo "</tr>"
    echo
  done
  cat <<EOF
    </table>
  </body>
</html>
EOF
}

make-job-wwz() {
  local job_id=${1:-test-job}

  local wwz=$job_id.wwz

  local index=_tmp/soil/INDEX.tsv 
  format-wwz-index $job_id $index > index.html

  # _tmp/soil: Logs are in _tmp, see soil/worker.sh
  # web/ : spec test HTML references this.
  #        Note that that index references /web/{base,soil}.css, outside the .wwz
  #        osh-summary.html uses table-sort.js and ajax.js
  # TODO: Could move _tmp/{spec,stateful,syscall} etc. to _test
  zip -q -r $wwz \
    index.html _tmp/soil _tmp/spec _tmp/stateful \
    _tmp/syscall _tmp/benchmark-data _tmp/metrics \
    _test \
    web/{base,spec-code,spec-tests,spec-cpp,line-counts}.css web/ajax.js \
    web/table/table-sort.{css,js} \
    _release/oil*.tar _release/VERSION/doc
}

deploy-job-results() {
  local prefix=$1
  shift
  # rest of args are more env vars

  local job_id="$(date +%Y-%m-%d__%H-%M-%S)"

  make-job-wwz $job_id

  # Debug permissions.  When using docker rather than podman, these dirs can be
  # owned by root and we can't write into them.
  ls -l -d _tmp/soil
  ls -l _tmp/soil

  date +%s > _tmp/soil/task-deploy-start-time.txt

  soil/collect_json.py _tmp/soil "$@" > $job_id.json

  # So we don't have to unzip it
  cp _tmp/soil/INDEX.tsv $job_id.tsv

  # Copy wwz, tsv, json
  scp-results "$prefix" $job_id.*

  log ''
  log 'View CI results here:'
  log ''
  log "http://travis-ci.oilshell.org/${prefix}jobs/"
  log "http://travis-ci.oilshell.org/${prefix}jobs/$job_id.wwz/"
  log ''
}

format-jobs-index() {
  soil-html-head 'Recent Jobs (raw data)'

  cat <<EOF
  <body class="width40">
    <p id="home-link">
      <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Recent Jobs (raw data)</h1>

    <table>
      <thead>
        <tr>
          <td>Job Archive</td>
          <td>JSON</td>
          <td>TSV</td>
        </tr>
      </thead>
EOF
  while read wwz; do
    local job_id=$(basename $wwz .wwz)
    echo '<tr>'
    echo "  <td><a href="$wwz/">$wwz</a></td>"
    if [[ $job_id == *test ]]; then
      # don't show misleading links
      echo "  <td>-</td>"
      echo "  <td>-</td>"
    else
      echo "  <td><a href="$job_id.json">JSON</a></td>"
      echo "  <td><a href="$job_id.tsv">TSV</a></td>"
    fi

    echo '</tr>'
  done

  cat <<EOF
    </table>
  </body>
</html>
EOF
}

write-jobs-raw() {
  ### Rewrite travis-ci.oilshell.org/jobs/raw.html
  local prefix=$1
  
  log "Listing remote .wwz"
  list-remote-results "$prefix" > _tmp/listing.txt
  ls -l _tmp/listing.txt

  # Pass all .wwz files in reverse order.
  # Empty list is OK.
  { egrep 'wwz$' _tmp/listing.txt || true; } \
    | sort --reverse \
    | format-jobs-index \
    > _tmp/raw.html

  log "Copying raw.html"

  scp-results "$prefix" _tmp/raw.html
}


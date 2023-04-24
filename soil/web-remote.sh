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
source test/tsv-lib.sh  # tsv2html
source web/table/html.sh  # table-sort-{begin,end}

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

my-scp() {
  scp -o StrictHostKeyChecking=no "$@"
}

my-ssh() {
  ssh -o StrictHostKeyChecking=no "$@"
}

scp-results() {
  # could also use Travis known_hosts addon?
  local prefix=$1  # srht- or ''
  shift

  my-scp "$@" "$SOIL_USER_HOST:travis-ci.oilshell.org/${prefix}jobs/"
}

scp-status-api() {
  local run_id=${1:-TEST2-github-run-id}
  local job_name=$2

  local status_file="_soil-jobs/$job_name.status.txt"
  local remote_path="travis-ci.oilshell.org/status-api/github/$run_id/$job_name"

  # We could make this one invocation of something like:
  # cat $status_file | sshq soil/web.sh PUT $remote_path

  my-ssh $SOIL_USER_HOST "mkdir -p $(dirname $remote_path)"

  # the consumer should check if these are all zero
  # note: the file gets RENAMED
  my-scp $status_file "$SOIL_USER_HOST:$remote_path"
}

list-remote-results() {
  local prefix=$1

  # Avoid race conditions with ls globbing
  my-ssh $SOIL_USER_HOST \
    "shopt -s nullglob
     cd travis-ci.oilshell.org/${prefix}jobs
     for i in */*; do echo \$i; done"
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
EOF

  if test -f _tmp/soil/image.html; then
    cat <<EOF
    <p>
      <a href="_tmp/soil/image.html">Container Image Stats</a>
    </p>
EOF
  fi

  cat <<EOF
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

format-image-stats() {
  local soil_dir=${1:-_tmp/soil}
  local web_base_url=${2:-'/web'}  # for production

  table-sort-html-head "Image Stats" $web_base_url

  # prints <body>; make it wide for the shell commands
  table-sort-begin "width60"

  # TODO:
  # - Format the TSV as an HTML table
  # - Save the name and tag and show it

  cat <<EOF
    <p id="home-link">
        <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Images Tagged</h1>

    <a href="images-tagged.txt">images-tagged.txt</a> <br/>

    <h1>Image Layers</h1>
EOF

  tsv2html $soil_dir/image-layers.tsv

  # First column is number of bytes; ignore header
  local total_bytes=$(awk '
      { sum += $1 }
  END { printf("%.1f", sum / 1000000) }
  ' $soil_dir/image-layers.tsv)

  echo "<p>Total Size: <b>$total_bytes MB</b></p>"


  cat <<EOF
    <h2>Raw Data</h2>

    <a href="image-layers.txt">image-layers.txt</a> <br/>
    <a href="image-layers.tsv">image-layers.tsv</a> <br/>
  </body>
</html>
EOF

  table-sort-end image-layers
}

make-job-wwz() {
  local job_id=${1:-test-job}

  local wwz=$job_id.wwz

  # Doesn't exist when we're not using a container
  if test -f _tmp/soil/image-layers.tsv; then
    format-image-stats _tmp/soil > _tmp/soil/image.html
  fi

  local index=_tmp/soil/INDEX.tsv 
  format-wwz-index $job_id $index > index.html

  # _tmp/soil: Logs are in _tmp, see soil/worker.sh
  # web/ : spec test HTML references this.
  #        Note that that index references /web/{base,soil}.css, outside the .wwz
  #        osh-summary.html uses table-sort.js and ajax.js
  #
  # TODO:
  # - Could move _tmp/{spec,stateful,syscall} etc. to _test
  # - Create _tmp/benchmarks/{compute,gc,gc-cachegrind,osh-parser,mycpp-examples,...}
  #   - would require release/$VERSION/pub/benchmarks.wwz, like we have
  #     pub/metrics.wwz, for consistent links

  zip -q -r $wwz \
    index.html \
    _test \
    _tmp/{soil,spec,wild-www,stateful,process-table,syscall,benchmark-data,metrics,mycpp-examples,compute,gc,gc-cachegrind,perf,vm-baseline,osh-runtime,osh-parser,host-id,shell-id} \
    _tmp/uftrace/{index.html,stage2} \
    web/{base,spec-code,spec-tests,spec-cpp,line-counts,benchmarks,wild}.css web/ajax.js \
    web/table/table-sort.{css,js} \
    _release/oil*.tar _release/VERSION/
}

deploy-job-results() {
  local prefix=$1  # e.g. example.com/github-jobs/
  local subdir=$2  # e.g. example.com/github-jobs/1234/  # make this dir
  local job_name=$3  # e.g. example.com/github-jobs/1234/foo.wwz
  shift 2
  # rest of args are more env vars

  # writes $job_name.wwz
  make-job-wwz $job_name

  # Debug permissions.  When using docker rather than podman, these dirs can be
  # owned by root and we can't write into them.
  ls -l -d _tmp/soil
  ls -l _tmp/soil

  date +%s > _tmp/soil/task-deploy-start-time.txt

  soil/collect_json.py _tmp/soil "$@" > $job_name.json

  # So we don't have to unzip it
  cp _tmp/soil/INDEX.tsv $job_name.tsv

  local remote_dest_dir="travis-ci.oilshell.org/${prefix}jobs/$subdir"
  my-ssh $SOIL_USER_HOST "mkdir -p $remote_dest_dir"

  # Do JSON last because that's what 'list-json' looks for
  my-scp $job_name.{wwz,tsv,json} "$SOIL_USER_HOST:$remote_dest_dir"

  log ''
  log 'View CI results here:'
  log ''
  log "http://travis-ci.oilshell.org/${prefix}jobs/$subdir/"
  log "http://travis-ci.oilshell.org/${prefix}jobs/$subdir/$job_name.wwz/"
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
    local prefix=${wwz%'.wwz'}

    echo '<tr>'
    echo "  <td><a href="$wwz/">$wwz</a></td>"
    echo "  <td><a href="$prefix.json">JSON</a></td>"
    echo "  <td><a href="$prefix.tsv">TSV</a></td>"
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

remote-event-job-done() {
  ### "Client side" handler: a job calls this when it's done
  local prefix=$1

  log "remote-event-job-done"

  # Deployed code dir
  sshq soil-web/soil/web.sh event-job-done "$@"

  # This does a remote ls and then an scp.  TODO: do we really need it?
  # Or change it to write to tmp file and atomically mv.
  write-jobs-raw $prefix
}

filename=$(basename $0)
if test $filename = web-remote.sh; then
  "$@"
fi


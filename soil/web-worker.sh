#!/usr/bin/env bash
#
# Functions to invoke soil/web remotely.
# 
# soil/web is deployed manually, and then this runs at HEAD in the repo.  Every
# CI run has an up-to-date copy.
#
# Usage:
#   soil/web-worker.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source soil/common.sh
source test/tsv-lib.sh  # tsv2html
source web/table/html.sh  # table-sort-{begin,end}

# ~/
#   soil-web/   # executable files
#    doctools/
#      html_head.py
#    soil/
#      web.py
#      web.sh
#   travis-ci.oilshell.org/  # served over HTTP
#     index.html
#     web/
#       base.css
#       soil.css
#     github-jobs/
#       index.html
#       3619/  # $GITHUB_RUN_NUMBER
#         dev-minimal.wwz
#         cpp-small.wwz
#     srht-jobs/
#       index.html
#       22/  # $JOB_ID
#         dev-minimal.wwz
#       23   # $JOB_ID
#         cpp-small.wwz

sshq() {
  # Don't need commands module as I said here!
  # http://www.oilshell.org/blog/2017/01/31.html
  #
  # This is Bernstein chaining through ssh.

  ssh $SOIL_USER@$SOIL_HOST "$(printf '%q ' "$@")"
}

remote-rewrite-jobs-index() {
  sshq soil-web/soil/web.sh rewrite-jobs-index "$@"
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

scp-results() {
  # could also use Travis known_hosts addon?
  local prefix=$1  # srht- or ''
  shift

  my-scp "$@" "$SOIL_USER_HOST:travis-ci.oilshell.org/${prefix}jobs/"
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

  soil-html-head "$job_id.wwz"

  cat <<EOF
  <body class="width40">
    <p id="home-link">
        <a href="..">Up</a>
      | <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>$job_id.wwz</h1>
EOF

  echo '<ul>'
  cat <<EOF
  <li>
    <a href="_tmp/soil/INDEX.tsv">_tmp/soil/INDEX.tsv</a>, also copied to
    <a href="../$job_id.tsv">../$job_id.tsv</a>.
  </li>
  <li>
    <a href="../$job_id.json">../$job_id.json</a>
  </li>
EOF

  if test -f _tmp/soil/image.html; then
    echo '
    <li>
      <a href="_tmp/soil/image.html">Container Image Stats</a>
    </li>
    '
  fi

  echo '</ul>'
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

  tsv2html3 $soil_dir/image-layers.tsv

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

  format-wwz-index $job_id > index.html

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
    _build/wedge/logs \
    _test \
    _tmp/{soil,spec,src-tree-www,wild-www,stateful,process-table,syscall,benchmark-data,metrics,mycpp-examples,compute,gc,gc-cachegrind,perf,vm-baseline,osh-runtime,osh-parser,host-id,shell-id} \
    _tmp/uftrace/{index.html,stage2} \
    web/{base,src-tree,spec-tests,spec-cpp,line-counts,benchmarks,wild}.css web/ajax.js \
    web/table/table-sort.{css,js} \
    _release/oil*.tar _release/*.xshar _release/VERSION/
}

test-collect-json() {
  soil/collect_json.py _tmp/soil PATH
}

deploy-job-results() {
  ### Copy .wwz, .tsv, and .json to a new dir

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

publish-cpp-tarball() {
  local prefix=${1:-'github-'}  # e.g. example.com/github-jobs/

  # Example of dir structure we need to cleanup:
  #
  # srht-jobs/
  #   git-$hash/
  #     index.html
  #     oils-for-unix.tar
  # github-jobs/
  #   git-$hash/
  #     oils-for-unix.tar
  #
  # Algorithm
  # 1. List all JSON, finding commit date and commit hash
  # 2. Get the OLDEST commit dates, e.g. all except for 50
  # 3. Delete all commit hash dirs not associated with them

  # Fix subtle problem here !!!
  shopt -s inherit_errexit

  local git_commit_dir
  git_commit_dir=$(git-commit-dir "$prefix")

  my-ssh $SOIL_USER_HOST "mkdir -p $git_commit_dir"

  # Do JSON last because that's what 'list-json' looks for

  local tar=_release/oils-for-unix.tar 

  # Permission denied because of host/guest issue
  #local tar_gz=$tar.gz
  #gzip -c $tar > $tar_gz

  # Avoid race condition
  # Crappy UUID: seconds since epoch, plus PID
  local timestamp
  timestamp=$(date +%s)

  local temp_name="tmp-$timestamp-$$.tar"

  my-scp $tar "$SOIL_USER_HOST:$git_commit_dir/$temp_name"

  my-ssh $SOIL_USER_HOST \
    "mv -v $git_commit_dir/$temp_name $git_commit_dir/oils-for-unix.tar"

  log 'Tarball:'
  log ''
  log "http://$git_commit_dir"
}

remote-event-job-done() {
  ### "Client side" handler: a job calls this when it's done

  log "remote-event-job-done"

  # Deployed code dir
  sshq soil-web/soil/web.sh event-job-done "$@"
}

filename=$(basename $0)
if test $filename = 'web-worker.sh'; then
  "$@"
fi

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
#     sourcehut-jobs/
#       index.html
#       22/  # $JOB_ID
#         dev-minimal.wwz
#       23   # $JOB_ID
#         cpp-small.wwz

sshq() {
  # Don't need commands module as I said here!
  # https://www.oilshell.org/blog/2017/01/31.html
  #
  # This is Bernstein chaining through ssh.

  my-ssh $SOIL_USER_HOST "$(printf '%q ' "$@")"
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
  #sshq soil-web/soil/web.sh cleanup-status-api false
  # 2024-07 - work around bug by doing dry_run only.
  #
  # TODO: Fix the logic in soil/web.sh

  if false; then
    sshq soil-web/soil/web.sh cleanup-status-api true
  else
    curl --include --fail-with-body \
      --form 'run-hook=soil-cleanup-status-api' \
      --form 'arg1=true' \
      $WWUP_URL
  fi
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
  local remote_path="$SOIL_REMOTE_DIR/status-api/github/$run_id/$job_name"

  # We could make this one invocation of something like:
  # cat $status_file | sshq soil/web.sh PUT $remote_path

  if false; then
    my-ssh $SOIL_USER_HOST "mkdir -p $(dirname $remote_path)"

    # the consumer should check if these are all zero
    # note: the file gets RENAMED
    my-scp $status_file "$SOIL_USER_HOST:$remote_path"
  else
    # Note: we don't need to change the name of the file, because we just glob
    # the dir
    curl --include --fail-with-body \
      --form 'payload-type=status-api' \
      --form "subdir=github/$run_id" \
      --form "file1=@$status_file" \
      $WWUP_URL
  fi
}

scp-results() {
  # could also use Travis known_hosts addon?
  local prefix=$1  # sourcehut- or ''
  shift

  my-scp "$@" "$SOIL_USER_HOST:$SOIL_REMOTE_DIR/${prefix}jobs/"
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

  soil-html-head "$job_id.wwz" /uuu/web

  cat <<EOF
  <body class="width40">
    <p id="home-link">
        <a href="..">Up</a>
      | <a href="/">Home</a>
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
        <a href="/">Home</a>
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
    _gen/mycpp/examples \
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

  local prefix=$1  # e.g. github- for example.com/github-jobs/
  local run_dir=$2  # e.g. 1234  # make this dir
  local job_name=$3  # e.g. cpp-small for example.com/github-jobs/1234/cpp-small.wwz
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

  if false; then
    local remote_dest_dir="$SOIL_REMOTE_DIR/${prefix}jobs/$run_dir"
    my-ssh $SOIL_USER_HOST "mkdir -p $remote_dest_dir"

    # Do JSON last because that's what 'list-json' looks for
    my-scp $job_name.{wwz,tsv,json} "$SOIL_USER_HOST:$remote_dest_dir"
  else
    curl --include --fail-with-body \
      --form "payload-type=${prefix}jobs" \
      --form "subdir=$run_dir" \
      --form "file1=@${job_name}.wwz" \
      --form "file2=@${job_name}.tsv" \
      --form "file3=@${job_name}.json" \
      $WWUP_URL
  fi

  log ''
  log 'View CI results here:'
  log ''
  log "https://$SOIL_HOST/uuu/${prefix}jobs/$run_dir/"
  log "https://$SOIL_HOST/uuu/${prefix}jobs/$run_dir/$job_name.wwz/"
  log ''
}

publish-cpp-tarball() {
  local prefix=${1:-'github-'}  # e.g. example.com/github-jobs/

  # Example of dir structure we need to cleanup:
  #
  # sourcehut-jobs/
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

  if false; then
    # Note: don't upload code without auth
    # TODO: Move it to a different dir.

    local commit_hash
    commit_hash=$(cat _tmp/soil/commit-hash.txt)

    local tar=_release/oils-for-unix.tar 
    curl --include --fail-with-body \
      --form 'payload-type=github-jobs' \
      --form "subdir=git-$commit_hash" \
      --form "file1=@$tar" \
      $WWUP_URL

    log 'Tarball:'
    log ''
    log "https://$SOIL_HOST/code/github-jobs/git-$commit_hash/"

  else
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
    log "https://$git_commit_dir"
  fi

}

remote-event-job-done() {
  ### "Client side" handler: a job calls this when it's done

  local prefix=$1  # 'github-' or 'sourcehut-'
  local run_id=$2  # $GITHUB_RUN_NUMBER or git-$hash

  log "remote-event-job-done $prefix $run_id"

  # Deployed code dir
  if false; then
    sshq soil-web/soil/web.sh event-job-done "$@"
  else
    # Note: I think curl does URL escaping of arg1= arg2= ?
    curl --include --fail-with-body \
      --form 'run-hook=soil-event-job-done' \
      --form "arg1=$prefix" \
      --form "arg2=$run_id" \
      $WWUP_URL
  fi
}

filename=$(basename $0)
if test $filename = 'web-worker.sh'; then
  "$@"
fi

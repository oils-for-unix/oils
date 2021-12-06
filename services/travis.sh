#!/usr/bin/env bash
#
# Automation for Travis CI.
#
# Usage:
#   services/travis.sh <function name>
#
# This contains setup for travis-ci.oilshell.org (the server), as well as the
# client, which is an ephemeral machine for each Travis run.
#
# The server needs a public key and the client needs a private key.
#
# Other TODO:
#
# And I probably need a cron job on my own domain to administer oilshell.org
# - wwz log files
#   - backup (does sync_logs.sh do this?)
#   - cleanup
# - clean up old travis CI build logs
# - back up /downloads/ dir
#
# Related docs:
#
# https://docs.travis-ci.com/user/environment-variables/#defining-encrypted-variables-in-travisyml

# https://oncletom.io/2016/travis-ssh-deploy/
# https://github.com/dwyl/learn-travis/blob/master/encrypted-ssh-keys-deployment.md

set -o nounset
set -o pipefail
set -o errexit

source services/common.sh

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

travis-html-head() {
  local title="$1"

  local base_url='../../web'

  # These files live at the root.  Bust cache.
  html-head --title "$title" "/web/base.css?cache=0" "/web/toil.css?cache=0" 
}

#
# Key Generation: One Time Setup
#

# Need to pass --pre because I hit this bug.  Does not inspire confidence.
# https://github.com/travis-ci/travis.rb/issues/711

deps() {
  # travis gem needed to encrypt ssh private key (also adds to .travis.yml)
  sudo gem install travis --pre  # --version '1.8.10'
}

keygen() {
  ssh-keygen -t rsa -b 4096 -C "travis-ci.oilshell" -f rsa_travis
}

encrypt-private-key() {
  ### Use travis gem to add an encrypted version to .travis.yml

  # 'travis login' first

  #travis encrypt-file ./rsa_travis --add
  travis encrypt-file ./rsa_travis services/rsa_travis.enc --add
}

deploy-public-key() {
  # note: permissions must be 700
  ssh travis_admin@travis-ci.oilshell.org mkdir -v -p .ssh

  # TODO: or append it?
  scp rsa_travis.pub travis_admin@travis-ci.oilshell.org:.ssh/authorized_keys
}

# Notes on setting up travis-ci.oilshell.org
#
# - Create the domain and user with dreamhost
# - Set it up to serve out of .wwz files (in dreamhost repo)
# - Deploy public key.  (Private key is encrypted and included in the repo.)

#
# Run inside the Travis build
#

readonly USER='travis_admin'
readonly HOST='travis-ci.oilshell.org'

home-page() {
  ### travis-ci.oilshell.org home page

  travis-html-head 'travis-ci.oilshell.org'
  cat <<EOF
  <body class="width40">
    <p id="home-link">
      <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>travis-ci.oilshell.org</h1>

    <p>This server receives results from cloud build services.
       See <a href="https://github.com/oilshell/oil/wiki/Toil">Toil</a> for details.
    </p>

    <ul>
      <li>
        <a href="srht-jobs/">sr.ht Jobs</a> from <a href="https://builds.sr.ht/~andyc">builds.sr.ht/~andyc</a>
      </li>
      <li>
        <a href="github-jobs/">Github Actions Jobs</a> from <a href="https://github.com/oilshell/oil/actions/workflows/all-builds.yml">github.com/oilshell/oil/actions/workflows/all-builds.yml</a>
      </li>
      <li>
        <a href="travis-jobs/">Travis Jobs</a> from <a href="https://app.travis-ci.com/github/oilshell/oil">app.travis-ci.com/oilshell/oil</a>
      </li>
      <li>
        <a href="builds/">Builds</a> (not yet implemented)
      </li>
    </ul>

  </body>
</html>
EOF
}

#
# ~/
#   toil-web/
#    doctools/
#      html_head.py
#    services/
#      toil_web.py
#      toil-web.sh
#   travis-ci.oilshell.org/
#     index.html
#     web/
#       base.css
#       toil.css
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

  ssh $USER@$HOST "$(printf '%q ' "$@")"
}

remote-rewrite-jobs-index() {
  local prefix=$1
  sshq toil-web/services/toil-web.sh rewrite-jobs-index "$prefix"
}

remote-cleanup-jobs-index() {
  local prefix=$1
  # clean it up for real!
  sshq toil-web/services/toil-web.sh cleanup-jobs-index "$prefix" false
}

init-server-html() {
  ssh $USER@$HOST mkdir -v -p $HOST/{travis-jobs,srht-jobs,github-jobs,web,builds/src}

  home-page > _tmp/index.html

  # note: duplicating CSS
  scp _tmp/index.html $USER@$HOST:$HOST/
  scp web/{base,toil}.css $USER@$HOST:$HOST/web
}

decrypt-key() {
  local out=$1
  openssl aes-256-cbc \
    -K $encrypted_a65247dffca0_key -iv $encrypted_a65247dffca0_iv \
    -in services/rsa_travis.enc -out $out -d
}

scp-results() {
  # could also use Travis known_hosts addon?
  local prefix=$1  # srht- or ''
  shift

  scp -o StrictHostKeyChecking=no "$@" \
    "travis_admin@travis-ci.oilshell.org:travis-ci.oilshell.org/${prefix}jobs/"
}

list-remote-results() {
  local prefix=$1
  ssh -o StrictHostKeyChecking=no \
    travis_admin@travis-ci.oilshell.org ls "travis-ci.oilshell.org/${prefix}jobs/"
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

  zip $wwz env.txt index.html build/*.txt

  scp-results '' $wwz
}

format-wwz-index() {
  ### What's displayed in $ID.wwz/index.html

  local job_id=$1
  local tsv=${2:-_tmp/toil/INDEX.tsv}

  travis-html-head "$job_id results"

  cat <<EOF
  <body class="width40">
    <p id="home-link">
      <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Job <code>$job_id</code></h1>

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
    echo "  <td><code><a href="_tmp/toil/logs/$task.txt">$task</a></code></td>"
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

# TODO: Extract this into a proper test
test-format-wwz-index() {
  services/toil-worker.sh run-dummy
  format-wwz-index DUMMY_JOB_ID
}

make-job-wwz() {
  local job_id=${1:-test-job}

  local wwz=$job_id.wwz

  local index=_tmp/toil/INDEX.tsv 
  format-wwz-index $job_id $index > index.html

  # _tmp/toil: Logs are in _tmp, see services/toil-worker.sh
  # mycpp/ : leave out bin/ for now
  # web/ : spec test HTML references this.
  #        Note that that index references /web/{base,toil}.css, outside the .wwz
  #        osh-summary.html uses table-sort.js and ajax.js
  zip -r $wwz \
    index.html _tmp/toil _tmp/spec _tmp/syscall _tmp/benchmark-data \
    mycpp/_ninja/*.{html,txt,tsv} mycpp/_ninja/{tasks,gen} \
    web/{base,spec-code,spec-tests,spec-cpp}.css web/ajax.js \
    web/table/table-sort.{css,js} \
    _release/oil.tar
}

deploy-job-results() {
  local prefix=$1
  shift
  # rest of args are more env vars

  local job_id="$(date +%Y-%m-%d__%H-%M-%S)"

  make-job-wwz $job_id

  # Debug permissions.  When using docker rather than podman, these dirs can be
  # owned by root and we can't write into them.
  ls -l -d _tmp/toil
  ls -l _tmp/toil

  date +%s > _tmp/toil/task-deploy-start-time.txt

  services/env_to_json.py _tmp/toil "$@" > $job_id.json

  # So we don't have to unzip it
  cp _tmp/toil/INDEX.tsv $job_id.tsv

  # Copy wwz, tsv, json
  scp-results "$prefix" $job_id.*

  log ''
  log "http://travis-ci.oilshell.org/${prefix}jobs/"
  log "http://travis-ci.oilshell.org/${prefix}jobs/$job_id.wwz/"
  log ''
}

format-jobs-index() {
  travis-html-head 'Recent Jobs (raw data)'

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

publish-html-assuming-ssh-key() {
  if true; then
    deploy-job-results 'travis-' \
      TRAVIS_JOB_NAME \
      TRAVIS_OS_NAME \
      TRAVIS_TIMER_START_TIME \
      TRAVIS_BUILD_WEB_URL \
      TRAVIS_JOB_WEB_URL \
      TRAVIS_BUILD_NUMBER \
      TRAVIS_JOB_NUMBER \
      TRAVIS_BRANCH \
      TRAVIS_COMMIT \
      TRAVIS_COMMIT_MESSAGE
  else
    deploy-test-wwz  # dummy data that doesn't depend on the build
  fi

  write-jobs-raw 'travis-'
  remote-rewrite-jobs-index 'travis-'

  # note: we could speed jobs up by doing this separately?
  remote-cleanup-jobs-index 'travis-'

  # toil-worker.sh recorded this for us
  return $(cat _tmp/toil/exit-status.txt)
}

publish-html() {
  local privkey=/tmp/rsa_travis

  decrypt-key $privkey
  chmod 600 $privkey
  eval "$(ssh-agent -s)"
  ssh-add $privkey

  publish-html-assuming-ssh-key
}

#
# Maintenance
#

# Sometimes the cache gets stale and you have to delete it.  Weird.
delete-caches() {
  travis cache -d
}

if test $(basename $0) = 'travis.sh'; then
  "$@"
fi

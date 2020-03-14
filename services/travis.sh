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

  # These files live at the root
  html-head --title "$title" "/web/base.css" "/web/toil.css" 
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

# Print the list of Travis jobs.
job-config() {
  # (artifact, platform)
  cat <<EOF
dev-minimal ubuntu-xenial
EOF
}

home-page() {
  ### travis-ci.oilshell.org home page

  travis-html-head 'travis.ci.oilshell.org'
  cat <<EOF
  <body class="width40">
    <p id="home-link">
      <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>travis-ci.oilshell.org</h1>

    <p>This server receives build results from 
       <a href="https://travis-ci.org/oilshell/oil">travis-ci.org/oilshell/oil</a>.
       See
       <a href="https://github.com/oilshell/oil/wiki/Travis-CI-for-Oil">Travis CI for Oil</a> for details.
    </p>

    <table>
      <thead>
        <tr>
          <td>Artifact</td>
          <td>Platform</td>
        </tr>
      </thead>
EOF
  job-config | while read artifact platform; do
    echo "<tr>"
    echo "  <td><a href="$artifact/">$artifact</a></td>"
    echo "  <td>$platform</td>"
    echo "</tr>"
    echo
  done
  cat <<EOF
    </table>
  </body>
</html>
EOF
}

init-server-html() {
  ssh $USER@$HOST mkdir -v -p $HOST/dev-minimal $HOST/web

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
  scp -o StrictHostKeyChecking=no "$@" \
    travis_admin@travis-ci.oilshell.org:travis-ci.oilshell.org/dev-minimal/
}

list-remote-results() {
  # could also use Travis known_hosts addon?
  ssh -o StrictHostKeyChecking=no \
    travis_admin@travis-ci.oilshell.org ls 'travis-ci.oilshell.org/dev-minimal/'
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

  scp-results $wwz
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
          <td>Status</td>
          <td>Elapsed</td>
          <td>Task Log</td>
          <td>Results</td>
        </tr>
      </thead>
EOF
  cat $tsv | while read status elapsed task script action result_html; do
    echo "<tr>"
    echo "  <td>$status</td>"
    echo "  <td>$elapsed</td>"
    echo "  <td><a href="_tmp/toil/$task.log.txt">$task</a></td>"

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

  local index=_tmp/toil/INDEX.tsv 
  format-wwz-index $job_id $index > index.html

  # _tmp/toil: Logs are in _tmp, see services/toil-worker.sh
  # web/ : spec test HTML references this.
  #        Note that that index references /web/{base,toil}.css, outside the .wwz
  zip -r $wwz index.html _tmp/toil _tmp/spec web/{base,spec-tests}.css
}

deploy-job-results() {
  local job_id="$(date +%Y-%m-%d__%H-%M-%S)"

  make-job-wwz $job_id

  services/env_to_json.py \
    TRAVIS_JOB_NAME \
    TRAVIS_OS_NAME \
    TRAVIS_TIMER_START_TIME \
    TRAVIS_BUILD_WEB_URL \
    TRAVIS_JOB_WEB_URL \
    TRAVIS_BUILD_NUMBER \
    TRAVIS_JOB_NUMBER \
    TRAVIS_BRANCH \
    TRAVIS_COMMIT \
    TRAVIS_COMMIT_MESSAGE \
    > $job_id.json

  # So we don't have to unzip it
  cp _tmp/toil/INDEX.tsv $job_id.tsv

  # Copy wwz, tsv, json
  scp-results $job_id.*

  log ''
  log "http://travis-ci.oilshell.org/dev-minimal/"
  log "http://travis-ci.oilshell.org/dev-minimal/$job_id.wwz/"
  log ''

  # TODO: git-log.txt, .json for hostname
  # - $job_id.git-log.txt: commit, branch, commit date, author?
  # - $job_id.json: hostname, date, etc.?
}

format-jobs-index() {
  travis-html-head 'dev-minimal jobs'

  cat <<EOF
  <body class="width40">
    <p id="home-link">
      <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Continuous Build: <code>dev-minimal</code> Jobs</h1>

    <table>
      <thead>
        <tr>
          <td>Task</td>
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

rewrite-job-index() {
  ### Rewrite travis-ci.oilshell.org/results/index.html
  
  # TODO: replace with toil_web.py?

  log "listing remote .wwz"
  list-remote-results > _tmp/listing.txt
  ls -l _tmp/listing.txt

  # Pass all .wwz files in reverse order.
  egrep 'wwz$' _tmp/listing.txt \
    | sort --reverse \
    | format-jobs-index \
    > _tmp/index.html

  log "copying index.html"

  # Duplicating CSS inside and OUTSIDE the .wwz files
  scp-results _tmp/index.html
}

publish-html() {
  local privkey=/tmp/rsa_travis

  decrypt-key $privkey
  chmod 600 $privkey
  eval "$(ssh-agent -s)"
  ssh-add $privkey

  if true; then
    deploy-job-results
  else
    deploy-test-wwz  # dummy data that doesn't depend on the build
  fi

  rewrite-job-index
}

# TODO:
#
# - job index
#   - print JSON fields: job URL, etc.
#   - SUM up the times
#   - SUM up the failures -- did it fail?
#     - do this in Python
#   - show commit description and diffstats
#     - you can embed this in the .wwz file
#
# Later:
# - spec test HTML
#
# Nice to have:
# - link to fast/compact git diff?  I don't like Githubs

"$@"

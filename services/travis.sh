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

log() {
  echo "$@" 1>&2
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

  cat <<EOF
<!DOCTYPE html>    
<html>
  <head>
    <title>travis-ci.oilshell.org</title>
    <link rel="stylesheet" type="text/css" href="base.css" />
    <link rel="stylesheet" type="text/css" href="toil.css" />
  </head>

  <body class="width40">
    <p id="home-link">
      <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>travis-ci.oilshell.org</h1>

    <table>
      <thead>
        <tr>
          <td>Platform</td>
        </tr>
      </thead>
EOF
  echo 'dev-minimal' | while read platform; do
    echo "<tr>"
    echo "  <td><a href="$platform/">$platform</a></td>"
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
  ssh $USER@$HOST mkdir -v -p $HOST/dev-minimal

  home-page > _tmp/index.html

  # note: duplicating CSS
  scp _tmp/index.html web/{base,toil}.css $USER@$HOST:$HOST/
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
  local out_name="$(date +%Y-%m-%d__%H-%M-%S)__$(hostname)"

  local wwz=$out_name.wwz

  cat >index.html <<EOF
<a href="build/oil-manifest.txt">build/oil-manifest.txt</a> <br/>
<a href="build/opy-manifest.txt">build/opy-manifest.txt</a> <br/>
EOF

  zip $wwz index.html build/*.txt

  scp-results $wwz
}

format-wwz-index() {
  ### What's displayed in $ID.wwz/index.html

  local job_id=$1
  local tsv=${2:-_tmp/toil/INDEX.tsv}

  cat <<EOF
<!DOCTYPE html>    
<html>
  <head>
    <title>Toil Results</title>
    <link rel="stylesheet" type="text/css" href="web/base.css" />
    <link rel="stylesheet" type="text/css" href="web/toil.css" />
  </head>

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
        </tr>
      </thead>
EOF
  cat $tsv | while read status elapsed task _; do
    echo "<tr>"
    echo "  <td>$status</td>"
    echo "  <td>$elapsed</td>"
    echo "  <td><a href="_tmp/toil/$task.log.txt">$task</a></td>"
    echo "</tr>"
    echo
  done
  cat <<EOF
    </table>
  </body>
</html>
EOF
}

make-results-wwz() {
  local job_id=${1:-test-job}

  local wwz=$job_id.wwz

  local index=_tmp/toil/INDEX.tsv 
  format-wwz-index $job_id $index > index.html

  # All the logs are here, see services/toil-worker.sh
  zip $wwz index.html web/{base,toil}.css _tmp/toil/*

}

deploy-results() {
  local job_id="$(date +%Y-%m-%d__%H-%M-%S)"

  make-results-wwz $job_id

  # So we don't have to unzip it
  cp _tmp/toil/INDEX.tsv $job_id.tsv

  # Copy all such files
  scp-results $job_id.*

  # TODO: git-log.txt, .json for hostname
  # - $job_id.git-log.txt: commit, branch, commit date, author?
  # - $job_id.json: hostname, date, etc.?
}

format-jobs-index() {
  cat <<EOF
<!DOCTYPE html>    
<html>
  <head>
    <title>Toil Results</title>
    <link rel="stylesheet" type="text/css" href="base.css" />
    <link rel="stylesheet" type="text/css" href="toil.css" />
  </head>

  <body class="width40">
    <p id="home-link">
      <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Continuous Build: <code>dev-minimal</code> Jobs</h1>

    <table>
      <thead>
        <tr>
          <td>Job ID</td>
        </tr>
      </thead>
EOF
  while read wwz; do
    echo '<tr>'
    echo "  <td><a href="$wwz/">$wwz</a></td>"
    echo '</tr>'
  done

  cat <<EOF
    </table>
  </body>
</html>
EOF
}

rewrite-index() {
  ### Rewrite travis-ci.oilshell.org/results/index.html
  
  # TODO: replace with toil_web.py?

  log "listing remote .wwz"
  list-remote-results > _tmp/listing.txt
  ls -l _tmp/listing.txt

  egrep 'wwz$' _tmp/listing.txt | format-jobs-index > _tmp/index.html

  log "copying index.html"

  # Duplicating CSS inside and OUTSIDE the .wwz files
  scp-results _tmp/index.html web/{base,toil}.css
}

publish-html() {
  local privkey=/tmp/rsa_travis

  decrypt-key $privkey
  chmod 600 $privkey
  eval "$(ssh-agent -s)"
  ssh-add $privkey

  #deploy-results
  #rewrite-index
  deploy-test-wwz
}

# TODO:
#
# - Share /web/*.css across all 3.  So it's always up to date and not cached.
# - Use html_head.py everywhere -- this is in benchmarks/common.sh
# - job index
#   - SUM up the times
#   - SUM up the failures -- did it fail?
#   - I guess do this with awk or something?
# - show commit description and diffstats
#   - you can embed this in the .wwz file
#
# Later:
# - spec test HTML
#
# Nice to have:
# - link to fast/compact git diff?  I don't like Githubs

"$@"

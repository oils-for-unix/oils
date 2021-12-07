#!/usr/bin/env bash
#
# Usage:
#   ./web-init.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source soil/common.sh  # for USER and HOST

# Notes on setting up travis-ci.oilshell.org
#
# - Create the domain and user with dreamhost
# - Set it up to serve out of .wwz files (in dreamhost repo)
# - Deploy public key.  (Private key is encrypted and included in the repo.)

#
# Run inside the Travis build
#

home-page() {
  ### travis-ci.oilshell.org home page

  soil-html-head 'travis-ci.oilshell.org'

  cat <<EOF
  <body class="width40">
    <p id="home-link">
      <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Soil on travis-ci.oilshell.org</h1>

    <p>This server receives results from cloud build services.
       See <a href="https://github.com/oilshell/oil/wiki/Soil">Soil</a> for details.
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

deploy-data() {
  ssh $USER@$HOST mkdir -v -p $HOST/{travis-jobs,srht-jobs,github-jobs,web,builds/src}

  home-page > _tmp/index.html

  # note: duplicating CSS
  scp _tmp/index.html $USER@$HOST:$HOST/
  scp web/{base,soil}.css $USER@$HOST:$HOST/web
}

soil-web-manifest() {
  PYTHONPATH=. /usr/bin/env python2 \
    build/app_deps.py py-manifest soil.web \
  | grep oilshell/oil  # only stuff in the repo

  # Add a shell script
  echo $PWD/soil/web.sh soil/web.sh
  echo $PWD/soil/common.sh soil/common.sh
}

# Also used in test/wild.sh
multi() { ~/git/tree-tools/bin/multi "$@"; }

deploy-code() {
  soil-web-manifest | multi cp _tmp/soil-web
  tree _tmp/soil-web
  rsync --archive --verbose _tmp/soil-web/ $USER@$HOST:soil-web/
}

deploy() {
  deploy-data
  deploy-code
}

remote-test() {
  ssh $USER@$HOST \
    soil-web/soil/web.sh smoke-test '~/travis-ci.oilshell.org/jobs'
}


"$@"

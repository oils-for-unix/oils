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

  local domain=${1:-'travis-ci.oilshell.org'}
  local title="Soil on $domain"
  soil-html-head "$title"

  cat <<EOF
  <body class="width40">
    <p id="home-link">
      <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>$title</h1>

    <p>This server receives results from cloud build services.
       See <a href="https://github.com/oilshell/oil/wiki/Soil">Soil</a> for details.
    </p>

    <table>
      <thead>
				<tr>
          <td>Recent Jobs</td>
          <td>Service Home</td>
          <td>Config</td>
				</tr>
      </thead>

      <tr>
        <td>
          <a href="srht-jobs/">sr.ht</a> 
        </td>
        <td>
          <a href="https://builds.sr.ht/~andyc">builds.sr.ht</a>
        </td>
        <td></td>
      </tr>

      <tr>
        <td>
          <a href="github-jobs/">Github Actions</a> 
        </td>
        <td>
          <a href="https://github.com/oilshell/oil/actions/workflows/all-builds.yml">github.com</a>
        </td>
        <td></td>
      </tr>

      <tr>
        <td>
          <a href="circle-jobs/">Circle CI</a> 
        </td>
        <td>
          <a href="https://app.circleci.com/pipelines/github/oilshell/oil">app.circleci.com</a>
        </td>
        <td></td>
      </tr>

      <tr>
        <td>
          <a href="cirrus-jobs/">Cirrus</a> 
        </td>
        <td>
          <a href="https://cirrus-ci.com/github/oilshell/oil">cirrus-ci.com</a>
        </td>
        <td></td>
      </tr>

      <tr>
        <td>
          <a href="travis-jobs/">Travis CI</a> (obsolete)
        </td>
        <td>
          <a href="https://app.travis-ci.com/github/oilshell/oil">app.travis-ci.com</a>
        </td>
        <td></td>
      </tr>

    </table>

  </body>
</html>
EOF
}

deploy-data() {
  local user=${1:-$USER}
  local host=${2:-$HOST}

  ssh $user@$host mkdir -v -p $host/{travis-jobs,srht-jobs,github-jobs,circle-jobs,cirrus-jobs,web}

  home-page "$host" > _tmp/index.html

  # note: duplicating CSS
  scp _tmp/index.html $user@$host:$host/
  scp web/{base,soil}.css $user@$host:$host/web
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

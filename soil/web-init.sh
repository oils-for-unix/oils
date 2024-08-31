#!/usr/bin/env bash
#
# Usage:
#   soil/web-init.sh <function name>
#
# Examples:
#   soil/web-init.sh deploy-data  # CSS, JS, etc.
#   soil/web-init.sh deploy-code  # web.py and its dependencies

set -o nounset
set -o pipefail
set -o errexit

source soil/common.sh  # for SOIL_USER and SOIL_HOST

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

  local domain=${1:-$SOIL_HOST}
  local title="Soil on $domain"
  soil-html-head "$title" 'uuu/web'

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
          <a href="uuu/github-jobs/">Github Actions</a> 
        </td>
        <td>
          <a href="https://github.com/oilshell/oil/actions/workflows/all-builds.yml">github.com</a>
        </td>
        <td>
          <a href="https://github.com/oils-for-unix/oils/tree/master/.github/workflows">.github/workflows</a>
        </td>
      </tr>

      <tr>
        <td>
          <a href="uuu/sourcehut-jobs/">sr.ht</a> 
        </td>
        <td>
          <a href="https://builds.sr.ht/~andyc">builds.sr.ht</a>
        </td>
        <td>
          <a href="https://github.com/oils-for-unix/oils/tree/master/.builds">.builds</a>
        </td>
      </tr>

EOF

  if false; then
    echo '
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
      '
  fi

  echo '
    </table>

    <h1>Links</h1>

    <ul>
      <li>
        <a href="code/github-jobs/">code/github-jobs/</a> - tarballs at every commit
      </li>
      <li>
        <a href="uuu/status-api/github/">uuu/static-api/github/</a> - files used by the CI
      </li>
    </ul>

  </body>
</html>
'
}

deploy-data() {
  local user=${1:-$SOIL_USER}
  local host=${2:-$SOIL_HOST}

  local host_dir=$SOIL_REMOTE_DIR

  # TODO: Better to put HTML in www/$host/uuu/github-jobs, etc.
  ssh $user@$host mkdir -v -p \
    $host_dir/uuu/{sourcehut-jobs,github-jobs,status-api/github} \
    $host_dir/uuu/web/table

  # Soil HTML has relative links like ../web/base.css, so we want
  # uuu/web/base.css
  #
  # note: duplicating CSS
  scp web/{base.css,soil.css,ajax.js} $user@$host:$host_dir/uuu/web
  scp web/table/*.{js,css} $user@$host:$host_dir/uuu/web/table

  home-page "$host" > _tmp/index.html
  scp _tmp/index.html $user@$host:$host_dir/
}

soil-web-manifest() {
  PYTHONPATH=. /usr/bin/env python2 \
    build/dynamic_deps.py py-manifest soil.web \
  | grep oilshell/oil  # only stuff in the repo

  # Add a shell script
  echo $PWD/soil/web.sh soil/web.sh
  echo $PWD/soil/common.sh soil/common.sh
}

# Also used in test/wild.sh
multi() { ~/git/tree-tools/bin/multi "$@"; }

deploy-code() {
  local user=${1:-$SOIL_USER}
  local host=${2:-$SOIL_HOST}

  soil-web-manifest | multi cp _tmp/soil-web
  tree _tmp/soil-web
  rsync --archive --verbose _tmp/soil-web/ $user@$host:soil-web/
}

deploy() {
  deploy-data "$@"
  deploy-code
}

remote-test() {
  local user=${1:-$SOIL_USER}
  local host=${2:-$SOIL_HOST}

  ssh $user@$host soil-web/soil/web.sh hello
}


"$@"

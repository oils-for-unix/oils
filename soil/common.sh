# Common functions for soil/

# Include guard.
test -n "${__SOIL_COMMON_SH:-}" && return
readonly __SOIL_COMMON_SH=1

log() {
  echo "$@" 1>&2
}

log-context() {
  local label=$1

  log ''
  log "$label: running as user '$(whoami)' on host '$(hostname)' in dir $PWD"
  log ''
}

dump-env() {
  env | grep -v '^encrypted_' | sort
}

# dh, mb, op
#_soil_service=op
#_soil_service=mb
_soil_service=dh

case $_soil_service in
  dh)
    readonly SOIL_USER='travis_admin'
    readonly SOIL_HOST='ci.oilshell.org'
    readonly SOIL_HOST_DIR=~/ci.oilshell.org  # used on server
    readonly SOIL_REMOTE_DIR=ci.oilshell.org  # used on client
    ;;
  mb)
    readonly SOIL_USER='oils'
    readonly SOIL_HOST='mb.oilshell.org'
    # Extra level
    readonly SOIL_HOST_DIR=~/www/mb.oilshell.org  # used on server
    readonly SOIL_REMOTE_DIR=www/mb.oilshell.org  # used on client
    ;;
  op)
    readonly SOIL_USER='oils'
    readonly SOIL_HOST='op.oilshell.org'
    readonly SOIL_HOST_DIR=~/op.oilshell.org  # used on server
    readonly SOIL_REMOTE_DIR=op.oilshell.org  # used on client
    ;;
  *)
    echo "Invalid Soil service $_soil_service" >& 2
    exit 1
    ;;
esac

readonly SOIL_USER_HOST="$SOIL_USER@$SOIL_HOST"

readonly WWUP_URL="https://$SOIL_HOST/uuu/wwup.cgi"

html-head() {
  # TODO: Shebang line should change too
  PYTHONPATH=. python3 doctools/html_head.py "$@"
}

# NOTE: soil-html-head and table-sort-html-head are distinct, because they
# collide with <td> styling and so forth

soil-html-head() {
  local title=$1
  local web_base_url=$2

  html-head --title "$title" \
    "$web_base_url/base.css?cache=0" "$web_base_url/soil.css?cache=0"
}

table-sort-html-head() {
  local title="$1"
  local web_base_url=${2:-'/web'}

  html-head --title "$title" \
    "$web_base_url/base.css?cache=0" \
    "$web_base_url/ajax.js?cache=0" \
    "$web_base_url/table/table-sort.css?cache=0" "$web_base_url/table/table-sort.js?cache=0" 
}

git-commit-dir() {
  local prefix=$1

  # written by save-metadata in soil/worker.sh
  local commit_hash
  commit_hash=$(cat _tmp/soil/commit-hash.txt)

  local git_commit_dir="$SOIL_REMOTE_DIR/code/${prefix}jobs/git-$commit_hash"

  echo $git_commit_dir
}

git-commit-url() {
  local prefix=$1

  # written by save-metadata in soil/worker.sh
  local commit_hash
  commit_hash=$(cat _tmp/soil/commit-hash.txt)

  # https:// not working on Github Actions because of cert issues?
  local url="https://$SOIL_HOST/code/${prefix}jobs/git-$commit_hash"

  echo $url
}

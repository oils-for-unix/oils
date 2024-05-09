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

readonly SOIL_USER='travis_admin'
readonly SOIL_HOST='travis-ci.oilshell.org'
readonly SOIL_USER_HOST="$SOIL_USER@$SOIL_HOST"

html-head() {
  # TODO: Shebang line should chang ecahnge to
  PYTHONPATH=. python3 doctools/html_head.py "$@"
}

# NOTE: soil-html-head and table-sort-html-head are distinct, because they
# collide with <td> styling and so forth

soil-html-head() {
  local title="$1"
  local web_base_url=${2:-'/web'}

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

  local commit_hash
  # written by save-metadata in soil/worker.sh
  commit_hash=$(cat _tmp/soil/commit-hash.txt)

  local git_commit_dir="travis-ci.oilshell.org/${prefix}jobs/git-$commit_hash"

  echo $git_commit_dir
}

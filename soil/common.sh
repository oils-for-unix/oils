# Common functions for soil/

log() {
  echo "$@" 1>&2
}

dump-env() {
  env | grep -v '^encrypted_' | sort
}

readonly USER='travis_admin'
readonly HOST='travis-ci.oilshell.org'

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

soil-html-head() {
  local title="$1"

  local base_url='../../web'

  # These files live at the root.  Bust cache.
  html-head --title "$title" "/web/base.css?cache=0" "/web/soil.css?cache=0" 
}


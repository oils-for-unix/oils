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
  # These files live at the root.  Bust cache.
  html-head --title "$title" "/web/base.css?cache=0" "/web/soil.css?cache=0" 
}

# Used by mycpp/build.sh and benchmarks/auto.sh
find-dir-html() {
  local dir=$1

  local txt=$dir/index.txt
  local html=$dir/index.html

  find $dir -type f | sort > $txt
  echo "Wrote $txt"

  # Note: no HTML escaping.  Would be nice for Oil.
  find $dir -type f | sort | gawk -v dir="$dir" '
  match($0, dir "/(.*)", m) {
    url = m[1]
    printf("<a href=\"%s\">%s</a> <br/>\n", url, url)
  }
  ' > $html

  echo "Wrote $html"
}

# Common functions for services/

log() {
  echo "$@" 1>&2
}

dump-env() {
  env | grep -v '^encrypted_' | sort
}

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


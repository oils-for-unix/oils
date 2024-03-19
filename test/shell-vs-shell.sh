#!/usr/bin/env bash
#
# Compare alternative shell designs!
#
# Usage:
#   test/shell-vs-shell.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BASE_DIR=_tmp/shell-vs-shell
readonly REPO_ROOT=$(cd $(dirname $0)/.. ; pwd)

readonly TAB=$'\t'

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

cmark() {
  # copied from build/doc.sh
  PYTHONPATH=. doctools/cmark.py --toc-tag h2 --toc-tag h3 --toc-pretty-href "$@"
}

highlight-code() {
  PYTHONPATH=. doctools/oils_doc.py highlight "$@"
}

desc() {
  echo "$@" > description.txt
}

src() {
  local lang=$1

  local prog=src/$lang

  # read from stdin
  cat > $prog

  case $lang in
    (oil)
      $REPO_ROOT/bin/oil $prog | tee output/$lang.txt
      ;;
    (shpp)
      ~/git/languages/shell-plus-plus/build/shell/shpp $prog | tee output/$lang.txt
      ;;
    (*)
      die "Invalid language $lang"
      ;;
  esac
}

CASE-hello() {

  desc "Print a string"

  # TODO:
  # - need to group these into a row somehow ...
  #   code-begin or something
  # - setup script
  # - show output in the HTML too
  #   - save that in a dir and then escape it

  src oil <<'EOF'
# oil requires quotes
echo 'hello world'

const name = 'world'
echo "hello $name"
EOF

  src shpp <<'EOF'
# no single quotes
echo hello world

name = "world"
echo "hello ${name}"  # braces required
EOF
}

CASE-pipeline() {
  desc 'Pipeline and Glob'

  touch src{1,2,3,4,5}

  src oil <<EOF
ls src* | sort -r | head -n 3
EOF

  src shpp <<EOF
ls src* | sort -r | head -n 3
EOF

}

CASE-try() {
  desc 'Error Handling'

  src oil <<'EOF'
# TODO: Oil could expose strerror() like shpp

try zzz
if (_status === 127) {
  echo "zzz not installed"
}
EOF

  src shpp <<'EOF'
try {
  zzz
} catch InvalidCmdException as ex {
  print("zzz not installed [msg: ", ex, "]")
}
EOF
}

CASE-read() {
  desc 'Read User Input'

  src oil <<'EOF'
echo hello | read --line

# _line starts with _, so it's a
# "register" mutated by the interpreter
echo "line: $_line"
EOF

  src shpp <<'EOF'
# not sure how to feed stdin

line = read()
print("line: ", line)
EOF
}

# TODO: Sort by section
CASE-ZZ-array() {
  desc 'Use Arrays'

  touch {foo,bar}.py

  src oil <<'EOF'
const array1 = ['physics', 'chemistry', 1997, 2000]
const array2 = [1, 2, 3, 4, 5, 6, 7]

write -- "array1[0]: $[array1[0]]"

# TODO: Oil needs @[]
const slice = array2[1:5]
write -- "array2[1:5]" @slice

# use the word language: bare words, glob, brace expansion
const shell_style = %( README.md *.py {alice,bob}@example.com )
write -- @shell_style
EOF

  src shpp <<'EOF'
array1 = ["physics", "chemistry", 1997, 2000];
array2 = [1, 2, 3, 4, 5, 6, 7 ];

print("array1[0]: ", array1[0])
print("array2[1:5]: ", array2[1:5])
EOF

}

CASE-path() {
  desc 'Test if path exists'

  src oil <<'EOF'
if test --exists /bin/grep {
  echo 'file exists'
}
EOF

  src shpp <<'EOF'
if path("/bin/grep").exists() {
  echo "file exists"
}
EOF
}

test-one() {
  local func_name=$1

  echo "$TAB---"
  echo "$TAB$func_name"
  echo "$TAB---"

  local dir=$BASE_DIR/$func_name

  mkdir -p $dir/{src,output}
  pushd $dir >/dev/null

  $func_name

  popd >/dev/null

}

test-all() {
  rm -r -f -v $BASE_DIR/
  mkdir -p $BASE_DIR/
  compgen -A function | grep '^CASE-' | xargs -n 1 -- $0 test-one

  tree $BASE_DIR
}

html-escape() {
  sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g' "$@"
}

html-footer() {
  echo '
  </body>
</html>
'
}

# TODO: Run through doctools plugin for syntax highlighting

make-table() {
  echo '<h2>'
  html-escape description.txt
  echo '</h2>'

  echo '<table>'
  echo '  <thead>'
  echo '  <tr>'
  echo '  <td></td>'
  for src_file in src/*; do 
    echo "<td>$(basename $src_file)</td>"
  done
  echo '  </tr>'
  echo '  </thead>'

  echo '  <tr>'
  echo '  <td>source</td>'
  for src_file in src/*; do 
    echo '<td><pre>'
    cat $src_file | html-escape
    echo '</pre></td>'
  done
  echo '  </tr>'

  echo '  <tr>'
  echo '  <td>output</td>'
  for out_file in output/*; do 
    echo '<td><pre>'
    cat $out_file | html-escape
    echo '</pre></td>'
  done
  echo '  </tr>'

  echo '</table>'
}


_html-all() {
  html-head --title 'Shell vs. Shell' \
    ../web/base.css ../web/shell-vs-shell.css ../web/language.css

  echo '<body class="width50">'

  cmark <<EOF
# Shell Design Comparison

This is a friendly comparison of the syntax of different shells!

- Oil: <https://github.com/oilshell/oil>
  - [A Tour of the Oil
    Language](https://www.oilshell.org/release/latest/doc/oil-language-tour.html)
- Shell++: <https://github.com/alexst07/shell-plus-plus>
  - [Shell++ Language Basics](https://alexst07.github.io/shell-plus-plus/lang-basics/)

&nbsp;

- More shells: <https://github.com/oilshell/oil/wiki/Alternative-Shells>
- Script that generates this file:
  <https://github.com/oilshell/oil/blob/master/test/shell-vs-shell.sh>

&nbsp;

EOF

  for dir in $BASE_DIR/CASE-*; do
    pushd $dir >/dev/null

    make-table

    popd >/dev/null
  done

  html-footer
}

html-all() {
  mkdir -p $BASE_DIR

  local out=$BASE_DIR/index.html

  _html-all | highlight-code > $out

  echo "Wrote $out"
}

all() {
  test-all
  html-all
}

"$@"

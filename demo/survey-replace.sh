#!/usr/bin/env bash
#
# Survey Python and JS string and regex replacement APIs
#
# Usage:
#   demo/survey-replace.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in $PATH

string() {
  echo 'STRING PYTHON'
  echo

  # This is a float
  python3 -c 'print("oils-for-unix".replace("i", "++"))'

  # replace none
  echo 'count=0'
  python3 -c 'print("oils-for-unix".replace("i", "++", 0))'
  echo

  # replace all
  echo 'count=-1'
  python3 -c 'print("oils-for-unix".replace("i", "++", -1))'
  echo

  # Very weird empty string behavior -- it finds one between every char
  python3 -c 'print("oils-for-unix".replace("", "++"))'
  python3 -c 'print("oils-for-unix".replace("", "++", 1))'
  echo

  echo 'STRING JS'
  echo
  # Only replaces first occurrence!
  # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/replace
  nodejs -e 'console.log("oils-for-unix".replace("i", "++"))'

  nodejs -e 'console.log("oils-for-unix".replace("", "++"))'
}

regex() {
  echo 'REGEX PYTHON'
  echo

  python3 -c 'import re; p = re.compile("[i]"); print(p.sub("++", "oils-for-unix"))'

  echo 'count=0 INCONSISTENT, replaces all'
  python3 -c 'import re; p = re.compile("[i]"); print(p.sub("++", "oils-for-unix", count=0))'
  echo

  echo 'count=-1'
  python3 -c 'import re; p = re.compile("[i]"); print(p.sub("++", "oils-for-unix", count=-1))'
  echo

  # empty string?
  # It's consistent, it finds empty string between every char
  python3 -c 'import re; p = re.compile(""); print(p.sub("++", "oils-for-unix"))'
  echo

  # supports equivalent of $0 and $1 ?
  python3 -c 'import re; p = re.compile("[i](.)"); print(p.sub("[\g<0>]", "oils-for-unix"))'
  python3 -c 'import re; p = re.compile("[i](.)"); print(p.sub("[\g<1>]", "oils-for-unix"))'
  echo

  echo 'REGEX JS'
  echo

  # Replaces first one
  nodejs -e 'console.log("oils-for-unix".replace(/[i]/, "++"))'

  # Replaces all
  # no count param?
  nodejs -e 'console.log("oils-for-unix".replace(/[i]/g, "++"))'

  # Empty regex
  nodejs -e 'console.log("oils-for-unix".replace(new RegExp(""), "++"))'

  # Hm this is inconsistent -- empty string gets replaced everywhere
  nodejs -e 'console.log("oils-for-unix".replace(new RegExp("", "g"), "++"))'

  # Hm JavaScript does not support $0 for the whole match -- it has $& instead
  # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/replace
  nodejs -e 'console.log("oils-for-unix".replace(new RegExp("[i](.)", "g"), "[$0]"))'
  nodejs -e 'console.log("oils-for-unix".replace(new RegExp("[i](.)", "g"), "[$&]"))'
  nodejs -e 'console.log("oils-for-unix".replace(new RegExp("[i](.)", "g"), "[$1]"))'
}

"$@"

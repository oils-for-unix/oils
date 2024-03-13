#!/usr/bin/env bash
#
# Survey string APIs
#
# Usage:
#   demo/survey-str-api.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in $PATH

# Python and JS string and regex replacement APIs

string-replace() {
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

regex-replace() {
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

  # ^ means that only one replacement occurs
  python3 -c 'import re; p = re.compile(r"(\d+)"); print(p.sub("[\g<1>]", "9-16-25\n100-200"))'
  echo
  python3 -c 'import re; p = re.compile(r"^(\d+)"); print(p.sub("[\g<1>]", "9-16-25\n100-200"))'
  echo
  # one replacement per line with re.MULTILINE!
  python3 -c 'import re; p = re.compile(r"^(\d+)", re.MULTILINE); print(p.sub("[\g<1>]", "9-16-25\n100-200"))'
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
  echo

  # ^ means that only one replacement occurs
  nodejs -e 'console.log("9-16-25\n100-200".replace(new RegExp("(\\d+)", "g"), "[$&]"))'
  echo
  nodejs -e 'console.log("9-16-25\n100-200".replace(new RegExp("^(\\d+)", "g"), "[$1]"))'
  echo
  # m flag is like re.MULTILINE
  nodejs -e 'console.log("9-16-25\n100-200".replace(new RegExp("^(\\d+)", "gm"), "[$1]"))'
  echo
}

survey-trim() {
  echo 'PYTHON'
  echo

  # TODO: Test other unicode chars
  local str=' hi '

  python3 -c 'import sys; s = sys.argv[1]; print("[%s] [%s]" % (s, s.strip()))' "$str"

  nodejs -e 'var s = process.argv[1]; var t = s.trim(); console.log(`[${s}] [${t}]`);' "$str"
}

"$@"

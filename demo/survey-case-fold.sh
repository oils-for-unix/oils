#!/usr/bin/env bash
#
# Usage:
#   demo/survey-case-fold.sh <function name>

# https://www.gnu.org/software/libc/manual/html_node/Locale-Names.html
# de_DE.UTF-8

show() {
  locale -a
  echo

  # https://serverfault.com/questions/54591/how-to-install-change-locale-on-debian

  cat /usr/share/i18n/SUPPORTED
  echo

  # German or Turkish
  cat /usr/share/i18n/SUPPORTED | egrep 'de_DE|tr_TR'
}

install() {
  # Otherwise I don't have Turkish and German
  sudo apt-get install locales
}

config() {
  # This is a GUI, which needs GUI
  #sudo dpkg-reconfigure locales

  # Uncomment en_US.UTF-8 for inclusion in generation
  sudo sed -i 's/^# *\(de_DE.UTF-8\)/\1/' /etc/locale.gen
  sudo sed -i 's/^# *\(tr_TR.UTF-8\)/\1/' /etc/locale.gen

  sudo locale-gen

  # Output
# Generating locales (this might take a while)...
#   de_DE.UTF-8... done
#   en_US.UTF-8... done
#   tr_TR.UTF-8... done
# Generation complete.
}

spec-tests() {
  test/spec.sh var-op-bash
  test/spec.sh ysh-func-builtin
}

# locale dependent
# https://stackoverflow.com/questions/30326167/getting-the-upper-or-lower-case-of-a-unicode-code-point-as-uint32-t

# Two issues
#
# - Does case folding depend on locale?
#   - No: Python
#   - Is it a global variable (bash) or a parameter (JavaScript)?
#
# - Does case folding take into account MULTIPLE code points?  Not multiple
#   bytes
#   - No: bash, Python 2
#   - Yes: Python 3, node.js


test-langs() {

  # OK this works
  export LANG=tr_TR.UTF-8

  #export LANG=de_DE.UTF-8

  bash << 'EOF'
echo shell
german=$'\u00DF'
turkish='i'
for small in $german $turkish; do
  echo u ${small^}
  echo U ${small^^}

  echo l ${small,}
  echo L ${small,,}

  echo
done

EOF
  echo

  echo python3
  python3 -c '
import sys

# Python case folding is NOT locale sensitive!
#
# https://stackoverflow.com/questions/19030948/python-utf-8-lowercase-turkish-specific-letter

import locale
#locale.setlocale(locale.LC_ALL, "tr_TR")
# Does not work?
#locale.setlocale(locale.LC_ALL, "tr_TR.UTF-8")
locale.setlocale(locale.LC_ALL, "tr_TR.utf8")

#print(sys.getdefaultencoding())

for small in [u"\u00DF", "i"]:
  sys.stdout.buffer.write(small.upper().encode("utf-8") + b"\n")
  sys.stdout.buffer.write(small.lower().encode("utf-8") + b"\n")

print()
big ="SS"
sys.stdout.buffer.write(big.upper().encode("utf-8") + b"\n")
sys.stdout.buffer.write(big.lower().encode("utf-8") + b"\n")

'
  echo

  echo node.js

  nodejs -e '
  for (small of ["\u00DF", "i", "SS"]) {
    console.log("no locale")
    console.log(small.toUpperCase())
    console.log(small.toLowerCase())
    console.log("")

    console.log("turkish")
    console.log(small.toLocaleUpperCase("tr"))
    console.log(small.toLocaleLowerCase("tr"))
    console.log("")

    console.log("german")
    console.log(small.toLocaleUpperCase("de"))
    console.log(small.toLocaleLowerCase("de"))
    console.log("")
  }
  console.log("")
  '
}

"$@"



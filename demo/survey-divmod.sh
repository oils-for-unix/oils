#!/usr/bin/env bash
#
# Survey division and modulus operators in variuos languages
#
# Usage:
#   demo/survey-divmod.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

div() {
  echo 'Python'
  python3 -c 'print(10 / -3); print(- 10 / 3)'
  python3 -c 'print(10 // -3); print(- 10 // 3)'
  python3 -c 'print(10 % -3); print(- 10 % 3); print (-10 % -3)'
  python3 -c 'print(10.0 % -3.0); print(- 10.0 % 3.0); print (-10.0 % -3.0)'
  echo 

  # Lua matches Python!
  echo 'Lua'
  lua -e 'print(10 / -3); print(- 10 / 3)'
  lua -e 'print(10 // -3); print(- 10 // 3)'
  lua -e 'print(10 % -3); print(- 10 % 3); print (-10 % -3)'
  lua -e 'print(10.0 % -3.0); print(- 10.0 % 3.0); print (-10.0 % -3.0)'
  echo 

  # JS and Awk match
  echo 'JS'
  nodejs -e 'console.log(10 / -3); console.log(- 10 / 3)'
  nodejs -e 'console.log(10 % -3); console.log(- 10 % 3); console.log(-10 % -3);'
  # no difference
  #nodejs -e 'console.log(10.0 % -3.0); console.log(- 10.0 % 3.0); console.log(-10.0 % -3.0);'
  echo 

  echo 'Perl'
  perl -e 'print 10 / -3 . "\n"; print - 10 / 3 . "\n"'
  # Perl modulus doesn't match Python/Lua or Awk/shell!
  perl -e 'print 10 % -3 . "\n"; print - 10 % 3 . "\n"; print -10 % -3 . "\n"'
  perl -e 'print 10.0 % -3.0 . "\n"; print - 10.0 % 3.0 . "\n"; print -10.0 % -3.0 . "\n"'
  echo 

  echo 'Awk'
  awk 'END { print(10 / -3); print (- 10 / 3) }' < /dev/null
  awk 'END { print(10 % -3); print (- 10 % 3); print(-10 % -3) }' < /dev/null
  echo 

  # bash only has integegers
  for sh in bash dash zsh; do
    echo $sh
    $sh -c 'echo $((10 / -3)); echo $((- 10 / 3))'
    $sh -c 'echo $((10 % -3)); echo $((- 10 % 3)); echo $((-10 % -3))'
    echo 
  done
}

# TODO:
# - Test invariants
# - OSH follows shells/awk/C
# - YSH could disallow negative numbers

"$@"

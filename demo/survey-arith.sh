#!/usr/bin/env bash
#
# Survey arithmetic in various languages
#
# Usage:
#   demo/survey-arith.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO:
# - Test invariants
# - OSH follows shells/awk/C
# - YSH could disallow negative numbers

divmod() {
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
# - Add Julia, Erlang, Elixir

bigint() {
  # Bigger than 2**64
  local big=11112222333344445555666677778888999

  # Big Int
  echo 'python3'
  python3 -c "print($big)"
  echo

  # Gets printed in scientific notation
  echo 'node.js'
  nodejs -e "console.log($big)"
  echo

  # Ditto, scientific
  echo 'Lua'
  lua -e "print($big)"
  echo

  # Scientific
  echo Perl
  perl -e "print $big"; echo
  echo

  # Awk loses precision somehow, not sure what they're doing
  echo awk
  awk -e "END { print $big }" < /dev/null
  echo

  local osh=_bin/cxx-dbg/osh
  ninja $osh

  for sh in dash bash mksh zsh $osh; do
    echo $sh
    $sh -c "echo \$(( $big ))" || true
    echo
  done

  # Julia has big integers
  echo 'Julia'
  demo/julia.sh julia -e "print($big)"; echo
  echo

  # None of the interpreters reject invalid input!  They tend to mangle the
  # numbers.
}

"$@"

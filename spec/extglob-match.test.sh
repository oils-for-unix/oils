#!/bin/bash
#
# Test matching with case
#
# Usage:
#   ./extglob-match.test.sh <function name>

#### @ matches exactly one
[[ --verbose == --@(help|verbose) ]] && echo TRUE
[[ --oops == --@(help|verbose) ]] || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### ? matches 0 or 1
[[ -- == --?(help|verbose) ]] && echo TRUE
[[ --oops == --?(help|verbose) ]] || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### + matches 1 or more
[[ --helphelp == --+(help|verbose) ]] && echo TRUE
[[ -- == --+(help|verbose) ]] || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### * matches 0 or more
[[ -- == --*(help|verbose) ]] && echo TRUE
[[ --oops == --*(help|verbose) ]] || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### simple repetition with *(foo) and +(Foo)
[[ foofoo == *(foo) ]] && echo TRUE
[[ foofoo == +(foo) ]] && echo TRUE
## stdout-json: "TRUE\nTRUE\n"

#### ! matches none
[[ --oops == --!(help|verbose) ]] && echo TRUE
[[ --help == --!(help|verbose) ]] || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### @() with variable arms
choice1='help'
choice2='verbose'
[[ --verbose == --@($choice1|$choice2) ]] && echo TRUE
[[ --oops == --@($choice1|$choice2) ]] || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### match is anchored
[[ foo_ == @(foo) ]] || echo FALSE
[[ _foo == @(foo) ]] || echo FALSE
[[ foo == @(foo) ]] && echo TRUE
## stdout-json: "FALSE\nFALSE\nTRUE\n"

#### repeated match is anchored
[[ foofoo_ == +(foo) ]] || echo FALSE
[[ _foofoo == +(foo) ]] || echo FALSE
[[ foofoo == +(foo) ]] && echo TRUE
## stdout-json: "FALSE\nFALSE\nTRUE\n"

#### repetition with glob
# NOTE that * means two different things here
[[ foofoo_foo__foo___ == *(foo*) ]] && echo TRUE
[[ Xoofoo_foo__foo___ == *(foo*) ]] || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### No brace expansion in ==
[[ --X{a,b}X == --@(help|X{a,b}X) ]] && echo TRUE
[[ --oops == --@(help|X{a,b}X) ]] || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### adjacent extglob
[[ --help == @(--|++)@(help|verbose) ]] && echo TRUE
[[ ++verbose == @(--|++)@(help|verbose) ]] && echo TRUE
## stdout-json: "TRUE\nTRUE\n"

#### nested extglob
[[ --help == --@(help|verbose=@(1|2)) ]] && echo TRUE
[[ --verbose=1 == --@(help|verbose=@(1|2)) ]] && echo TRUE
[[ --verbose=2 == --@(help|verbose=@(1|2)) ]] && echo TRUE
[[ --verbose == --@(help|verbose=@(1|2)) ]] || echo FALSE
## stdout-json: "TRUE\nTRUE\nTRUE\nFALSE\n"

#### extglob in variable
shopt -s extglob
g=--@(help|verbose)
quoted='--@(help|verbose)'
[[ --help == $g ]] && echo TRUE
[[ --verbose == $g ]] && echo TRUE
[[ -- == $g ]] || echo FALSE
[[ --help == $q ]] || echo FALSE
[[ -- == $q ]] || echo FALSE
## stdout-json: "TRUE\nTRUE\nFALSE\nFALSE\nFALSE\n"
## N-I mksh stdout-json: "FALSE\nFALSE\nFALSE\n"

#### extglob empty string
shopt -s extglob
[[ '' == @(foo|bar) ]] || echo FALSE
[[ '' == @(foo||bar) ]] && echo TRUE
## stdout-json: "FALSE\nTRUE\n"

#### extglob empty pattern
shopt -s extglob
[[ '' == @() ]] && echo TRUE
[[ '' == @(||) ]] && echo TRUE
[[ X == @() ]] || echo FALSE
[[ '|' == @(||) ]] || echo FALSE
## stdout-json: "TRUE\nTRUE\nFALSE\nFALSE\n"

#### case with extglob
shopt -s extglob
for word in --help --verbose --unmatched -- -zxzx -; do
  case $word in
    --@(help|verbose) )
      echo A
      continue
      ;;
    ( --?(b|c) )
      echo B
      continue
      ;;
    ( -+(x|z) )
      echo C
      continue
      ;;
    ( -*(x|z) )
      echo D
      continue
      ;;
    *)
      echo U
      continue
      ;;
  esac
done
## stdout-json: "A\nA\nU\nB\nC\nD\n"

#### Without shopt -s extglob
empty=''
str='x'
[[ $empty == !($str) ]] && echo TRUE  # test glob match
[[ $str == !($str) ]]   || echo FALSE
## stdout-json: "TRUE\nFALSE\n"

#### Turning extglob on changes the meaning of [[ !(str) ]] in bash
empty=''
str='x'
[[ !($empty) ]]  && echo TRUE   # test if $empty is empty
[[ !($str) ]]    || echo FALSE  # test if $str is empty
shopt -s extglob  # mksh doesn't have this
[[ !($empty) ]]  && echo TRUE   # negated glob
[[ !($str) ]]    && echo TRUE   # negated glob
## stdout-json: "TRUE\nFALSE\nTRUE\nTRUE\n"
## OK mksh stdout-json: "TRUE\nTRUE\nTRUE\n"

#### With extglob on, !($str) on the left or right of == has different meanings
shopt -s extglob
empty=''
str='x'
[[ 1 == !($str) ]]  && echo TRUE   # glob match
[[ !($str) == 1 ]]  || echo FALSE  # test if empty
# NOTE: There cannot be a space between ! and (?
## stdout-json: "TRUE\nFALSE\n"

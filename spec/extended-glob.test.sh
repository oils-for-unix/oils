#!/usr/bin/env bash
#
# This is an OPTION in bash, but not mksh (because the feature originated in
# ksh).
#
# However all extended globs are syntax errors if shopt -s extglob isn't set,
# so I'm not sure what the point of having the option is.  We should always
# parse it?
#
# It's also now a GNU libc extension to glob() and fnmatch() with FNM_EXTMATCH.
# However, this came after shells!  Not sure who uses it.  Does musl have it?
#
# I guess this is handy because it's like *.[ch]... but the extensions can be
# different length.
# 
# Although brace substitution can do this: *.{cc,h}.

# "In addition to the traditional globs (supported by all Bourne-family shells)
# that we've seen so far, Bash (and Korn Shell) offers extended globs, which
# have the expressive power of regular expressions. Korn shell enables these by
# default; in Bash, you must run the command "

# ?(pattern-list): Matches empty or one of the patterns
# *(pattern-list): Matches empty or any number of occurrences of the patterns
# +(pattern-list): Matches at least one occurrences of the patterns
# @(pattern-list): Matches exactly one of the patterns
# !(pattern-list): Matches anything EXCEPT any of the patterns

### @() extended glob
shopt -s extglob
touch _tmp/{foo,bar}.cc _tmp/{foo,bar,baz}.h
echo _tmp/@(*.cc|*.h)
# stdout: _tmp/bar.cc _tmp/bar.h _tmp/baz.h _tmp/foo.cc _tmp/foo.h

### ?() extended glob
# matches the empty string too
shopt -s extglob
touch _tmp/{foo,bar}.cc _tmp/{foo,bar,baz}.h
echo _tmp/?(*.cc|*.h)
# stdout: _tmp/bar.cc _tmp/bar.h _tmp/baz.h _tmp/foo.cc _tmp/foo.h

### *() matches multiple copies
shopt -s extglob
mkdir -p _tmp/eg1
touch _tmp/eg1/One _tmp/eg1/OneOne _tmp/eg1/TwoTwo _tmp/eg1/OneTwo
echo _tmp/eg1/*(One|Two)
# stdout: _tmp/eg1/One _tmp/eg1/OneOne _tmp/eg1/OneTwo _tmp/eg1/TwoTwo

### !(*.h) to match everything except headers
shopt -s extglob
mkdir -p _tmp/extglob2
touch _tmp/extglob2/{foo,bar}.cc _tmp/extglob2/{foo,bar,baz}.h
echo _tmp/extglob2/!(*.h)
# stdout: _tmp/extglob2/bar.cc _tmp/extglob2/foo.cc

### glob spaces
shopt -s extglob
mkdir -p _tmp/eg4
touch _tmp/eg4/a '_tmp/eg4/a b' _tmp/eg4/foo
argv.py _tmp/eg4/@(a b|foo)
# stdout: ['_tmp/eg4/a b', '_tmp/eg4/foo']

### glob other punctuation chars (lexer mode)
# mksh sorts them differently
shopt -s extglob
mkdir -p _tmp/eg5
cd _tmp/eg5
touch __{'<>','{}','|','#','&&'}
argv.py @('__<>'|__{}|__\||__#|__&&)
# stdout: ['__<>', '__|', '__{}', '__&&', '__#']
# OK mksh stdout: ['__#', '__&&', '__<>', '__{}', '__|']

### @ matches exactly one
[[ --verbose == --@(help|verbose) ]] && echo TRUE
[[ --oops == --@(help|verbose) ]] || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### ? matches 0 or 1
[[ -- == --?(help|verbose) ]] && echo TRUE
[[ --oops == --?(help|verbose) ]] || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### + matches 1 or more
[[ --helphelp == --+(help|verbose) ]] && echo TRUE
[[ -- == --+(help|verbose) ]] || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### * matches 0 or more
[[ -- == --*(help|verbose) ]] && echo TRUE
[[ --oops == --*(help|verbose) ]] || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### simple repetition with *(foo) and +(Foo)
[[ foofoo == *(foo) ]] && echo TRUE
[[ foofoo == +(foo) ]] && echo TRUE
# stdout-json: "TRUE\nTRUE\n"

### ! matches none
[[ --oops == --!(help|verbose) ]] && echo TRUE
[[ --help == --!(help|verbose) ]] || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### @() with variable arms
choice1='help'
choice2='verbose'
[[ --verbose == --@($choice1|$choice2) ]] && echo TRUE
[[ --oops == --@($choice1|$choice2) ]] || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### match is anchored
[[ foo_ == @(foo) ]] || echo FALSE
[[ _foo == @(foo) ]] || echo FALSE
[[ foo == @(foo) ]] && echo TRUE
# stdout-json: "FALSE\nFALSE\nTRUE\n"

### repeated match is anchored
[[ foofoo_ == +(foo) ]] || echo FALSE
[[ _foofoo == +(foo) ]] || echo FALSE
[[ foofoo == +(foo) ]] && echo TRUE
# stdout-json: "FALSE\nFALSE\nTRUE\n"

### repetition with glob
# NOTE that * means two different things here
[[ foofoo_foo__foo___ == *(foo*) ]] && echo TRUE
[[ Xoofoo_foo__foo___ == *(foo*) ]] || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### No brace expansion in ==
[[ --X{a,b}X == --@(help|X{a,b}X) ]] && echo TRUE
[[ --oops == --@(help|X{a,b}X) ]] || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### adjacent extglob
[[ --help == @(--|++)@(help|verbose) ]] && echo TRUE
[[ ++verbose == @(--|++)@(help|verbose) ]] && echo TRUE
# stdout-json: "TRUE\nTRUE\n"

### nested extglob
[[ --help == --@(help|verbose=@(1|2)) ]] && echo TRUE
[[ --verbose=1 == --@(help|verbose=@(1|2)) ]] && echo TRUE
[[ --verbose=2 == --@(help|verbose=@(1|2)) ]] && echo TRUE
[[ --verbose == --@(help|verbose=@(1|2)) ]] || echo FALSE
# stdout-json: "TRUE\nTRUE\nTRUE\nFALSE\n"

### extglob in variable
shopt -s extglob
g=--@(help|verbose)
quoted='--@(help|verbose)'
[[ --help == $g ]] && echo TRUE
[[ --verbose == $g ]] && echo TRUE
[[ -- == $g ]] || echo FALSE
[[ --help == $q ]] || echo FALSE
[[ -- == $q ]] || echo FALSE
# stdout-json: "TRUE\nTRUE\nFALSE\nFALSE\nFALSE\n"
# N-I mksh stdout-json: "FALSE\nFALSE\nFALSE\n"

### extglob empty string
shopt -s extglob
[[ '' == @(foo|bar) ]] || echo FALSE
[[ '' == @(foo||bar) ]] && echo TRUE
# stdout-json: "FALSE\nTRUE\n"

### extglob empty pattern
shopt -s extglob
[[ '' == @() ]] && echo TRUE
[[ '' == @(||) ]] && echo TRUE
[[ X == @() ]] || echo FALSE
[[ '|' == @(||) ]] || echo FALSE
# stdout-json: "TRUE\nTRUE\nFALSE\nFALSE\n"

### printing extglob in variable
# mksh does static parsing so it doesn't like this?
shopt -s extglob
mkdir -p _tmp/eg3
touch _tmp/eg3/{foo,bar}
g=_tmp/eg3/@(foo|bar)
echo $g "$g"  # quoting inhibits globbing
# stdout: _tmp/eg3/bar _tmp/eg3/foo _tmp/eg3/@(foo|bar)
# N-I mksh stdout: _tmp/eg3/@(foo|bar) _tmp/eg3/@(foo|bar)

### case with extglob
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
# stdout-json: "A\nA\nU\nB\nC\nD\n"

### Without shopt -s extglob
empty=''
str='x'
[[ $empty == !($str) ]] && echo TRUE  # test glob match
[[ $str == !($str) ]]   || echo FALSE
# stdout-json: "TRUE\nFALSE\n"

### Turning extglob on changes the meaning of [[ !(str) ]] in bash
empty=''
str='x'
[[ !($empty) ]]  && echo TRUE   # test if $empty is empty
[[ !($str) ]]    || echo FALSE  # test if $str is empty
shopt -s extglob  # mksh doesn't have this
[[ !($empty) ]]  && echo TRUE   # negated glob
[[ !($str) ]]    && echo TRUE   # negated glob
# stdout-json: "TRUE\nFALSE\nTRUE\nTRUE\n"
# OK mksh stdout-json: "TRUE\nTRUE\nTRUE\n"

### With extglob on, !($str) on the left or right of == has different meanings
shopt -s extglob
empty=''
str='x'
[[ 1 == !($str) ]]  && echo TRUE   # glob match
[[ !($str) == 1 ]]  || echo FALSE  # test if empty
# NOTE: There cannot be a space between ! and (?
# stdout-json: "TRUE\nFALSE\n"

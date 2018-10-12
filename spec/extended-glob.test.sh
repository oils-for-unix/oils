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

#### @() extended glob
shopt -s extglob
touch _tmp/{foo,bar}.cc _tmp/{foo,bar,baz}.h
echo _tmp/@(*.cc|*.h)
## stdout: _tmp/bar.cc _tmp/bar.h _tmp/baz.h _tmp/foo.cc _tmp/foo.h

#### ?() extended glob
# matches the empty string too
shopt -s extglob
touch _tmp/{foo,bar}.cc _tmp/{foo,bar,baz}.h
echo _tmp/?(*.cc|*.h)
## stdout: _tmp/bar.cc _tmp/bar.h _tmp/baz.h _tmp/foo.cc _tmp/foo.h

#### *() matches multiple copies
shopt -s extglob
mkdir -p _tmp/eg1
touch _tmp/eg1/One _tmp/eg1/OneOne _tmp/eg1/TwoTwo _tmp/eg1/OneTwo
echo _tmp/eg1/*(One|Two)
## stdout: _tmp/eg1/One _tmp/eg1/OneOne _tmp/eg1/OneTwo _tmp/eg1/TwoTwo

#### !(*.h) to match everything except headers
shopt -s extglob
mkdir -p _tmp/extglob2
touch _tmp/extglob2/{foo,bar}.cc _tmp/extglob2/{foo,bar,baz}.h
echo _tmp/extglob2/!(*.h)
## stdout: _tmp/extglob2/bar.cc _tmp/extglob2/foo.cc

#### glob spaces
shopt -s extglob
mkdir -p _tmp/eg4
touch _tmp/eg4/a '_tmp/eg4/a b' _tmp/eg4/foo
argv.py _tmp/eg4/@(a b|foo)
## stdout: ['_tmp/eg4/a b', '_tmp/eg4/foo']

#### glob other punctuation chars (lexer mode)
# mksh sorts them differently
shopt -s extglob
mkdir -p _tmp/eg5
cd _tmp/eg5
touch __{'<>','{}','|','#','&&'}
argv.py @('__<>'|__{}|__\||__#|__&&)
## stdout: ['__<>', '__|', '__{}', '__&&', '__#']
## OK mksh stdout: ['__#', '__&&', '__<>', '__{}', '__|']

#### printing extglob in variable
# mksh does static parsing so it doesn't like this?
shopt -s extglob
mkdir -p _tmp/eg3
touch _tmp/eg3/{foo,bar}
g=_tmp/eg3/@(foo|bar)
echo $g "$g"  # quoting inhibits globbing
## stdout: _tmp/eg3/bar _tmp/eg3/foo _tmp/eg3/@(foo|bar)
## N-I mksh stdout: _tmp/eg3/@(foo|bar) _tmp/eg3/@(foo|bar)

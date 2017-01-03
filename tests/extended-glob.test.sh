#!/bin/bash
#
# This is an OPTION in bash, but not mksh (because the feature originated in
# ksh).  So it's probably low priority.
#
# It's also now a GNU libc extension to glob() and fnmatch().
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
# how is this different than the above?
shopt -s extglob
touch _tmp/{foo,bar}.cc _tmp/{foo,bar,baz}.h
echo _tmp/?(*.cc|*.h)
# stdout: _tmp/bar.cc _tmp/bar.h _tmp/baz.h _tmp/foo.cc _tmp/foo.h

### !() extended glob
# Hm this syntax isn't right?
shopt -s extglob
touch _tmp/{a,b}.R _tmp/{a,b}_test.R
echo */*.R!(*_test.R)
# stdout: _tmp/a.R _tmp/b.R

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

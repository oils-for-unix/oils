#!/usr/bin/env bash
#
# Corner cases in var sub.  Maybe rename this file.

#### Bad var sub
echo ${a|}
## stdout-json: ""
## status: 2
## OK bash/mksh status: 1

#### Braced block inside ${}
# NOTE: This bug was in bash 4.3 but fixed in bash 4.4.
echo ${foo:-$({ which ls; })}
## stdout: /bin/ls

#### Nested ${} 
bar=ZZ
echo ${foo:-${bar}}
## stdout: ZZ

#### Filename redirect with "$@" 
# bash - ambiguous redirect -- yeah I want this error
#   - But I want it at PARSE time?  So is there a special DollarAtPart?
#     MultipleArgsPart?
# mksh - tries to create '_tmp/var-sub1 _tmp/var-sub2'
# dash - tries to create '_tmp/var-sub1 _tmp/var-sub2'
fun() {
  echo hi > "$@"
}
fun _tmp/var-sub1 _tmp/var-sub2
## status: 1
## OK dash status: 2

#### Filename redirect with split word
# bash - runtime error, ambiguous redirect
# mksh and dash - they will NOT apply word splitting after redirect, and write
# to '_tmp/1 2'
# Stricter behavior seems fine.
foo='_tmp/1 2'
rm '_tmp/1 2'
echo hi > $foo
test -f '_tmp/1 2' && cat '_tmp/1 2'
## status: 0
## stdout: hi
## OK bash status: 1
## OK bash stdout-json: ""

#### Descriptor redirect to bad "$@"
# All of them give errors:
# dash - bad fd number, parse error?
# bash - ambiguous redirect
# mksh - illegal file descriptor name
set -- '2 3' 'c d'
echo hi 1>& "$@"
## status: 1
## OK dash status: 2

#### Here doc with bad "$@" delimiter
# bash - syntax error
# dash - syntax error: end of file unexpected
# mksh - runtime error: here document unclosed
#
# What I want is syntax error: bad delimiter!
#
# This means that "$@" should be part of the parse tree then?  Anything that
# involves more than one token.
fun() {
  cat << "$@"
hi
1 2
}
fun 1 2
## status: 2
## stdout-json: ""
## OK mksh status: 1

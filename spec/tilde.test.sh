#!/usr/bin/env bash

#### ~ expansion in assignment
HOME=/home/bob
a=~/src
echo $a
## stdout: /home/bob/src

#### ~ expansion in readonly assignment
# dash fails here!
# http://stackoverflow.com/questions/8441473/tilde-expansion-doesnt-work-when-i-logged-into-gui
HOME=/home/bob
readonly const=~/src
echo $const
## stdout: /home/bob/src
## BUG dash stdout: ~/src

#### No ~ expansion in dynamic assignment
HOME=/home/bob
binding='const=~/src'
readonly "$binding"
echo $const
## stdout: ~/src

#### No tilde expansion in word that looks like assignment but isn't
# bash and mksh mistakenly expand here!
# bash fixes this in POSIX mode (gah).
# http://lists.gnu.org/archive/html/bug-bash/2016-06/msg00001.html
HOME=/home/bob
echo x=~
## stdout: x=~
## BUG bash/mksh stdout: x=/home/bob

#### tilde expansion of word after redirect
HOME=$TMP
echo hi > ~/tilde1.txt
cat $HOME/tilde1.txt | wc -c
## stdout: 3
## status: 0

#### other user
echo ~nonexistent
## stdout: ~nonexistent

#!/bin/bash
#
# let arithmetic.

### let
# NOTE: no spaces are allowed.  How is this tokenized?
let x=1
let y=x+2
let z=y*3  # zsh treats this as a glob; bash doesn't
let z2='y*3'  # both are OK with this
echo $x $y $z $z2
# stdout: 1 3 9 9
# OK zsh stdout-json: ""

### let with ()
let x=( 1 )
let y=( x + 2 )
let z=( y * 3 )
echo $x $y $z
# stdout: 1 3 9
# N-I mksh/zsh stdout-json: ""

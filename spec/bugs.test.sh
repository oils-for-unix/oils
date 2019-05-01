#!/usr/bin/env bash

#### echo keyword
echo done
## stdout: done

#### if/else
if false; then
  echo THEN
else
  echo ELSE
fi
## stdout: ELSE

#### Turn an array into an integer.
a=(1 2 3)
(( a = 42 )) 
echo $a
## stdout: 42
## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2


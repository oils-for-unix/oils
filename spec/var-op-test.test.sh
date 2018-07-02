#!/usr/bin/env bash

#### Lazy Evaluation of Alternative
i=0
x=x
echo ${x:-$((i++))}
echo $i
echo ${undefined:-$((i++))}
echo $i  # i is one because the alternative was only evaluated once
## status: 0
## stdout-json: "x\n0\n0\n1\n"
## N-I dash status: 2
## N-I dash stdout-json: "x\n0\n"

#### Default value when empty
empty=''
echo ${empty:-is empty}
## stdout: is empty

#### Default value when unset
echo ${unset-is unset}
## stdout: is unset

#### Unquoted with array as default value
set -- '1 2' '3 4'
argv.py X${unset=x"$@"x}X
## stdout: ['Xx1', '2', '3', '4xX']

#### Quoted with array as default value
set -- '1 2' '3 4'
argv.py "X${unset=x"$@"x}X"
## stdout: ['Xx1 2 3 4xX']
## BUG bash stdout: ['Xx1', '2', '3', '4xX']

#### Assign default value when empty
empty=''
${empty:=is empty}
echo $empty
## stdout: is empty

#### Assign default value when unset
${unset=is unset}
echo $unset
## stdout: is unset

#### Assign default with array
#    HMMMM osh stdout-json: "['Xx1 2', '3 4xX']\n['x1 2 3 4x']\n"
#    I think OSH diverges here because VTest is different than VOp1?
#    I parse all the arg words the same way.
set -- '1 2' '3 4'
argv.py X${unset=x"$@"x}X
argv.py "$unset"
## stdout-json: "['Xx1', '2', '3', '4xX']\n['x1 2 3 4x']\n"

#### Alternative value when empty
v=foo
empty=''
echo ${v:+v is not empty} ${empty:+is not empty}
## stdout: v is not empty

#### Alternative value when unset
v=foo
echo ${v+v is not unset} ${unset:+is not unset}
## stdout: v is not unset

#### Error when empty
empty=''
${empty:?is empty}
## status: 1
## OK dash status: 2

#### Error when unset
${unset?is empty}
## status: 1
## OK dash status: 2

#### Error when unset
v=foo
echo ${v+v is not unset} ${unset:+is not unset}
## stdout: v is not unset

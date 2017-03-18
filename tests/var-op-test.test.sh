#!/bin/bash

### Lazy Evaluation of Alternative
i=0
x=x
echo ${x:-$((i++))}
echo $i
echo ${undefined:-$((i++))}
echo $i  # i is one because the alternative was only evaluated once
# status: 0
# stdout-json: "x\n0\n0\n1\n"
# N-I dash status: 2
# N-I dash stdout-json: "x\n0\n"

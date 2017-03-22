#!/bin/bash

### Remove smallest suffix
v=aabbccdd
echo ${v%c*}
# stdout: aabbc

### Remove longest suffix
v=aabbccdd
echo ${v%%c*}
# stdout: aabb

### Remove smallest prefix
v=aabbccdd
echo ${v#*b}
# stdout: bccdd

### Remove longest prefix
v=aabbccdd
echo ${v##*b}
# stdout: ccdd


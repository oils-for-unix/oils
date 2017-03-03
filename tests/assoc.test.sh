#!/bin/bash

# NOTE:
# -declare -A is required.
#
# Simply doing:
# a=([aa]=b [foo]=bar ['a+1']=c)
# gets utterly bizarre behavior.
#
# Associtative Arrays are COMPLETELY bash-specific.  mksh doesn't even come
# close.  So I will probably not implement them, or implement something
# slightly different, because the semantics are just wierd.

# http://www.gnu.org/software/bash/manual/html_node/Arrays.html
# TODO: Need a SETUP section.

### TODO: SETUP should be share
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)

### retrieve indices with !
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
argv.py "${!a[@]}"
# Is this invalid on associative arrays?  Makes no sense.
# stdout: ['aa', 'foo', 'a+1']

### $a gives nothing
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
echo "${a}"
# stdout-json: "\n"

### length of dict does not work
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
echo "${#a}"
# stdout: 0

### index by number doesn't work
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
echo 0 "${a[0]}" 1 "${a[1]}" 2 "${a[2]}"
# stdout-json: "0  1  2 \n"

### index by key name
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
echo "${a[aa]}" "${a[foo]}" "${a['a+1']}"
# WTF: Why do we get bar bar c?
# stdout-json: "b bar c\n"

### index by quoted string
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
echo "${a['a+1']}"
# stdout: c

### index by unquoted string
declare -A a
a=([aa]=b [foo]=bar ['a+1']=c)
echo "${a[a+1]}"
# stdout: c

### index by unquoted string as arithmetic
# For assoc arrays, unquoted string is just raw.
# For regular arrays, unquoted string is an arithmetic expression!
# How do I parse this?
declare -A assoc
assoc=([a+1]=c)
array=(5 6 7)
a=1
echo "${assoc[a]}" 
echo "${assoc[a+1]}"  # This works
echo "${array[a+1]}"
# stdout-json: "\nc\n7\n"

### WTF index by key name
declare -A a
a=([xx]=bb [cc]=dd)
echo "${a[xx]}" "${a[cc]}"
# stdout-json: "bb dd\n"

### Array stored in associative array gets converted to string
array=('1 2' 3)
declare -A d
d[a]="${array[@]}"
argv.py "${d[a]}"
# stdout: ['1 2 3']

### Can't initialize assoc array with indexed array
declare -A A=(1 2 3)
# status: 1
# BUG bash status: 0

### Initializing indexed array with with assoc array drops the constants
declare -a a=([xx]=1 [yy]=2 [zz]=3)
#declare -a a=(1 2 3)
echo "${a[@]}"
#echo "${!a[@]}"
# N-I mksh stdout-json: ""
# BUG bash stdout-json: "3\n"

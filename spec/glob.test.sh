#!/usr/bin/env bash
#
# NOTE: Could move spec/03-glob.sh here.

### glob double quote escape
echo "*.sh"
# stdout: *.sh

### glob single quote escape
echo "*.sh"
# stdout: *.sh

### glob backslash escape
echo \*.sh
# stdout: *.sh

### 1 char glob
echo [b]in
# stdout: bin

### 0 char glob -- does NOT work
echo []bin
# stdout: []bin

### looks like glob at the start, but isn't
echo [bin
# stdout: [bin

### looks like glob plus negation at the start, but isn't
echo [!bin
# stdout: [!bin

### glob can expand to command and arg
spec/echo.s[hz]
# stdout: spec/echo.sz

### glob after var expansion
touch _tmp/a.A _tmp/aa.A _tmp/b.B
f="_tmp/*.A"
g="$f _tmp/*.B"
echo $g
# stdout: _tmp/a.A _tmp/aa.A _tmp/b.B

### quoted var expansion with glob meta characters
touch _tmp/a.A _tmp/aa.A _tmp/b.B
f="_tmp/*.A"
echo "[ $f ]"
# stdout: [ _tmp/*.A ]

### glob after "$@" expansion
func() {
  echo "$@"
}
func '_tmp/*.B'
# stdout: _tmp/*.B

### glob after $@ expansion
func() {
  echo $@
}
func '_tmp/*.B'
# stdout: _tmp/b.B

### no glob after ~ expansion
HOME=*
echo ~/*.py
# stdout: */*.py

### store literal globs in array then expand
touch _tmp/a.A _tmp/aa.A _tmp/b.B
g=("_tmp/*.A" "_tmp/*.B")
echo ${g[@]}
# stdout: _tmp/a.A _tmp/aa.A _tmp/b.B
# N-I dash/ash stdout-json: ""
# N-I dash/ash status: 2

### glob inside array
touch _tmp/a.A _tmp/aa.A _tmp/b.B
g=(_tmp/*.A _tmp/*.B)
echo "${g[@]}"
# stdout: _tmp/a.A _tmp/aa.A _tmp/b.B
# N-I dash/ash stdout-json: ""
# N-I dash/ash status: 2

### glob with escaped - in char class
touch _tmp/foo.-
touch _tmp/c.C
echo _tmp/*.[C-D] _tmp/*.[C\-D]
# stdout: _tmp/c.C _tmp/c.C _tmp/foo.-

### glob with char class expression
# note: mksh doesn't support [[:punct:]] ?
touch _tmp/e.E _tmp/foo.-
echo _tmp/*.[[:punct:]E]
# stdout: _tmp/e.E _tmp/foo.-
# BUG mksh stdout: _tmp/*.[[:punct:]E]

### glob double quotes
# note: mksh doesn't support [[:punct:]] ?
touch _tmp/\"quoted.py\"
echo _tmp/\"*.py\"
# stdout: _tmp/"quoted.py"

### glob escaped
# - mksh doesn't support [[:punct:]] ?
# - python shell fails because \[ not supported!
touch _tmp/\[abc\] _tmp/\?
echo _tmp/\[???\] _tmp/\?
# stdout: _tmp/[abc] _tmp/?

### : escaped
touch _tmp/foo.-
echo _tmp/*.[[:punct:]] _tmp/*.[[:punct\:]]
# stdout: _tmp/foo.- _tmp/*.[[:punct:]]
# BUG mksh stdout: _tmp/*.[[:punct:]] _tmp/*.[[:punct:]]

### Redirect to glob, not evaluated
# This writes to *.F, not foo.F
rm _tmp/*.F
touch _tmp/f.F
echo foo > _tmp/*.F
cat '_tmp/*.F'
# status: 0
# stdout: foo
# BUG bash status: 1
# BUG bash stdout-json: ""

### Glob after var manipulation
touch _tmp/foo.zzz _tmp/bar.zzz
g='_tmp/*.zzzZ'
echo $g ${g%Z}
# stdout: _tmp/*.zzzZ _tmp/bar.zzz _tmp/foo.zzz

### Glob after part joining
touch _tmp/foo.yyy _tmp/bar.yyy
g='_tmp/*.yy'
echo $g ${g}y
# stdout: _tmp/*.yy _tmp/bar.yyy _tmp/foo.yyy

### Glob flags on file system
touch _tmp/-n _tmp/zzzzz
cd _tmp
echo -* hello zzzz?
# stdout-json: "hello zzzzz"

### Don't glob flags on file system with GLOBIGNORE
# This is a bash-specific extension.
expr $0 : '.*/osh$' >/dev/null && exit 99  # disabled until cd implemented
touch _tmp/-n _tmp/zzzzz
cd _tmp  # this fail in osh
GLOBIGNORE=-*:zzzzz  # colon-separated pattern list
echo -* hello zzzz?
# stdout-json: "-* hello zzzz?\n"
# N-I dash/mksh/ash stdout-json: "hello zzzzz"
# status: 0

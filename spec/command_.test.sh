#!/usr/bin/env bash
#
# Miscellaneous tests for the command language.

#### Command block
{ which ls; }
## stdout: /bin/ls

#### Permission denied
touch $TMP/text-file
$TMP/text-file
## status: 126

#### Not a dir
$TMP/not-a-dir/text-file
## status: 127

#### Name too long
./0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789
## status: 127
## OK dash status: 2
## OK bash status: 126

#### External programs don't have _OVM in environment
# bug fix for leakage
env | grep _OVM
echo status=$?
## stdout: status=1

#### File with no shebang is executed
# most shells execute /bin/sh; bash may execute itself
echo 'echo hi' > $TMP/no-shebang
chmod +x $TMP/no-shebang
$SH -c '$TMP/no-shebang'
## stdout: hi
## status: 0

#### File with relative path and no shebang is executed
SH="$(realpath "$SH")"
cd $TMP
echo 'echo hi' > no-shebang
chmod +x no-shebang
"$SH" -c ./no-shebang
## stdout: hi
## status: 0

#### File in relative subdirectory and no shebang is executed
SH="$(realpath "$SH")"
cd $TMP
mkdir test-no-shebang
echo 'echo hi' > test-no-shebang/script
chmod +x test-no-shebang/script
"$SH" -c test-no-shebang/script
## stdout: hi
## status: 0

#### $PATH lookup
cd $TMP
mkdir -p one two
echo 'echo one' > one/mycmd
echo 'echo two' > two/mycmd
chmod +x one/mycmd two/mycmd

PATH='one:two'
mycmd
## STDOUT:
one
## END

#### filling $PATH cache, then insert the same command earlier in cache
cd $TMP
PATH="one:two:$PATH"
mkdir -p one two
rm -f one/* two/*
echo 'echo two' > two/mycmd
chmod +x two/mycmd
mycmd

# Insert earlier in the path
echo 'echo one' > one/mycmd
chmod +x one/mycmd
mycmd  # still runs the cached 'two'

# clear the cache
hash -r
mycmd  # now it runs the new 'one'

## STDOUT:
two
two
one
## END

# zsh doesn't do caching!
## OK zsh STDOUT:
two
one
one
## END

#### filling $PATH cache, then deleting command
cd $TMP
PATH="one:two:$PATH"
mkdir -p one two
rm -f one/mycmd two/cmd

echo 'echo two' > two/mycmd
chmod +x two/mycmd
mycmd
echo status=$?

# Insert earlier in the path
echo 'echo one' > one/mycmd
chmod +x one/mycmd
rm two/mycmd
mycmd  # still runs the cached 'two'
echo status=$?

## STDOUT:
two
status=0
status=127
## END

# mksh and zsh correctly searches for the executable again!
## OK zsh/mksh STDOUT:
two
status=0
one
status=0
## END

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
cd $TMP
echo 'echo hi' > no-shebang
chmod +x no-shebang
"$SH" -c './no-shebang'
## stdout: hi
## status: 0

#### File in relative subdirectory and no shebang is executed
cd $TMP
mkdir -p test-no-shebang
echo 'echo hi' > test-no-shebang/script
chmod +x test-no-shebang/script
"$SH" -c 'test-no-shebang/script'
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
rm -f one/mycmd two/mycmd

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

#### Non-executable on $PATH

# shells differ in whether they actually execve('one/cmd') and get EPERM

cd $TMP
PATH="one:two:$PATH"
mkdir -p one two
rm -f one/mycmd two/mycmd

echo 'echo one' > one/mycmd
echo 'echo two' > two/mycmd

# only make the second one executable
chmod +x two/mycmd
mycmd
echo status=$?
## STDOUT:
two
status=0
## END

#### hash without args prints the cache
whoami >/dev/null
hash
echo status=$?
## STDOUT:
/usr/bin/whoami
status=0
## END

# bash uses a weird table.  Although we could use TSV2.
## OK bash stdout-json: "hits\tcommand\n   1\t/usr/bin/whoami\nstatus=0\n"

## OK mksh/zsh STDOUT:
whoami=/usr/bin/whoami
status=0
## END

#### hash with args
hash whoami
echo status=$?
hash | grep -o /whoami  # prints it twice
hash _nonexistent_
echo status=$?
## STDOUT:
status=0
/whoami
status=1
## END

# mksh doesn't fail
## BUG mksh STDOUT:
status=0
/whoami
status=0
## END

#### hash -r doesn't allow additional args
hash -r whoami >/dev/null  # avoid weird output with mksh
echo status=$?
## stdout: status=1
## OK osh stdout: status=2
## BUG dash/bash stdout: status=0

## oils_failures_allowed: 16
## compare_shells: bash


#### help
help
echo status=$? >&2
help help
echo status=$? >&2
help -- help
echo status=$? >&2
## STDERR:
status=0
status=0
status=0
## END

#### bad help topic
help ZZZ 2>$TMP/err.txt
echo "help=$?"
cat $TMP/err.txt | grep -i 'no help topics' >/dev/null
echo "grep=$?"
## STDOUT: 
help=1
grep=0
## END

#### type -t -> function
f() { echo hi; }
type -t f
## stdout: function

#### type -t -> alias
shopt -s expand_aliases
alias foo=bar
type -t foo
## stdout: alias

#### type -t -> builtin
type -t echo read : [ declare local
## STDOUT:
builtin
builtin
builtin
builtin
builtin
builtin
## END

#### type -t -> keyword
type -t for time ! fi do {
## STDOUT: 
keyword
keyword
keyword
keyword
keyword
keyword
## END

#### type -t control flow

# this differs from bash, but don't lie!
type -t break continue return exit
## STDOUT:
keyword
keyword
keyword
keyword
## END
## OK bash STDOUT:
builtin
builtin
builtin
builtin
## END


#### type -t -> file
type -t find xargs
## STDOUT: 
file
file
## END

#### type -t doesn't find non-executable (like command -v)
PATH="$TMP:$PATH"
touch $TMP/non-executable
type -t non-executable
## STDOUT:
## END
## status: 1
## BUG bash STDOUT:
file
## END
## BUG bash status: 0

#### type -t -> not found
type -t echo ZZZ find =
echo status=$?
## STDOUT: 
builtin
file
status=1
## END
## STDERR:
## END

#### type -> not found
type zz 2>err.txt
echo status=$?
grep -o 'not found' err.txt
## STDOUT:
status=1
not found
## END

#### type -p and -P builtin -> file
touch /tmp/{mv,tar,grep}
chmod +x /tmp/{mv,tar,grep}
PATH=/tmp:$PATH

type -p mv tar grep
echo --
type -P mv tar grep
## STDOUT:
/tmp/mv
/tmp/tar
/tmp/grep
--
/tmp/mv
/tmp/tar
/tmp/grep
## END

#### type -p builtin -> not found
type -p FOO BAR NOT_FOUND
## status: 1
## STDOUT:
## END

#### type -p builtin -> not a file
type -p cd type builtin command
## STDOUT:
## END

#### type -P builtin -> not found
type -P FOO BAR NOT_FOUND
## status: 1
## STDOUT:
## END

#### type -P builtin -> not a file
type -P cd type builtin command
## status: 1
## STDOUT:
## END

#### type -P builtin -> not a file but file found
touch /tmp/{mv,tar,grep}
chmod +x /tmp/{mv,tar,grep}
PATH=/tmp:$PATH

mv () { ls; }
tar () { ls; }
grep () { ls; }
type -P mv tar grep cd builtin command type
## status: 1
## STDOUT:
/tmp/mv
/tmp/tar
/tmp/grep
## END

#### type -f builtin -> not found
type -f FOO BAR NOT FOUND
## status: 1

#### type -f builtin -> function and file exists
touch /tmp/{mv,tar,grep}
chmod +x /tmp/{mv,tar,grep}
PATH=/tmp:$PATH

mv () { ls; }
tar () { ls; }
grep () { ls; }
type -f mv tar grep
## STDOUT:
/tmp/mv is a file
/tmp/tar is a file
/tmp/grep is a file
## OK bash STDOUT:
mv is /tmp/mv
tar is /tmp/tar
grep is /tmp/grep
## END

#### type -a -> function
f () { :; }
type -a f
## STDOUT:
f is a function
f () 
{ 
    :
}
## END

#### type -ap -> function
f () { :; }
type -ap f
## STDOUT:
## END

#### type -a -> alias
shopt -s expand_aliases
alias ll="ls -lha"
type -a ll
## stdout: ll is aliased to `ls -lha'

#### type -ap -> alias
shopt -s expand_aliases
alias ll="ls -lha"
type -ap ll
## STDOUT:
## END

#### type -a -> builtin
type -a cd
## stdout: cd is a shell builtin

#### type -ap -> builtin
type -ap cd
## STDOUT:
## END

#### type -a -> keyword
type -a while
## stdout: while is a shell keyword

#### type -a -> file
type -a date
## stdout: date is /bin/date

#### type -ap -> file
type -ap date
## stdout: /bin/date

#### type -a -> builtin and file
type -a pwd
## STDOUT:
pwd is a shell builtin
pwd is /bin/pwd
## END

#### type -ap -> builtin and file
type -ap pwd
## stdout: /bin/pwd

#### type -a -> executable not in PATH
touch /tmp/executable
chmod +x /tmp/executable
type -a executable
## status: 1

#### mapfile
type mapfile >/dev/null 2>&1 || exit 0
printf '%s\n' {1..5..2} | {
  mapfile
  echo "n=${#MAPFILE[@]}"
  printf '[%s]\n' "${MAPFILE[@]}"
}
## STDOUT:
n=3
[1
]
[3
]
[5
]
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### readarray (synonym for mapfile)
type readarray >/dev/null 2>&1 || exit 0
printf '%s\n' {1..5..2} | {
  readarray
  echo "n=${#MAPFILE[@]}"
  printf '[%s]\n' "${MAPFILE[@]}"
}
## STDOUT:
n=3
[1
]
[3
]
[5
]
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### mapfile (array name): arr
type mapfile >/dev/null 2>&1 || exit 0
printf '%s\n' {1..5..2} | {
  mapfile arr
  echo "n=${#arr[@]}"
  printf '[%s]\n' "${arr[@]}"
}
## STDOUT:
n=3
[1
]
[3
]
[5
]
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### mapfile (delimiter): -d delim
# Note: Bash-4.4+
type mapfile >/dev/null 2>&1 || exit 0
printf '%s:' {1..5..2} | {
  mapfile -d : arr
  echo "n=${#arr[@]}"
  printf '[%s]\n' "${arr[@]}"
}
## STDOUT:
n=3
[1:]
[3:]
[5:]
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### mapfile (delimiter): -d '' (null-separated)
# Note: Bash-4.4+
type mapfile >/dev/null 2>&1 || exit 0
printf '%s\0' {1..5..2} | {
  mapfile -d '' arr
  echo "n=${#arr[@]}"
  printf '[%s]\n' "${arr[@]}"
}
## STDOUT:
n=3
[1]
[3]
[5]
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### mapfile (truncate delim): -t
type mapfile >/dev/null 2>&1 || exit 0
printf '%s\n' {1..5..2} | {
  mapfile -t arr
  echo "n=${#arr[@]}"
  printf '[%s]\n' "${arr[@]}"
}
## STDOUT:
n=3
[1]
[3]
[5]
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### mapfile -t doesn't remove \r
type mapfile >/dev/null 2>&1 || exit 0
printf '%s\r\n' {1..5..2} | {
  mapfile -t arr
  argv.py "${arr[@]}"
}
## STDOUT:
['1\r', '3\r', '5\r']
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### mapfile (store position): -O start
type mapfile >/dev/null 2>&1 || exit 0
printf '%s\n' a{0..2} | {
  arr=(x y z)
  mapfile -O 2 -t arr
  echo "n=${#arr[@]}"
  printf '[%s]\n' "${arr[@]}"
}
## STDOUT:
n=5
[x]
[y]
[a0]
[a1]
[a2]
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### mapfile (input range): -s start -n count
type mapfile >/dev/null 2>&1 || exit 0
printf '%s\n' a{0..10} | {
  mapfile -s 5 -n 3 -t arr
  echo "n=${#arr[@]}"
  printf '[%s]\n' "${arr[@]}"
}
## STDOUT:
n=3
[a5]
[a6]
[a7]
## END
## N-I dash/mksh/zsh/ash STDOUT:
## END

#### mapfile / readarray stdin  TODO: Fix me.
shopt -s lastpipe  # for bash

seq 2 | mapfile m
seq 3 | readarray r
echo ${#m[@]}
echo ${#r[@]}
## STDOUT:
2
3
## END

#
# Test the length oeprator, which dash supports.  Dash doesn't support most
# other ops.

#### String length
v=foo
echo ${#v}
## stdout: 3

#### Unicode string length (UTF-8)
v=$'_\u03bc_'
echo ${#v}
## stdout: 3
## N-I dash stdout: 9
## N-I mksh stdout: 4

#### Unicode string length (spec/testdata/utf8-chars.txt)
v=$(cat $REPO_ROOT/spec/testdata/utf8-chars.txt)
echo ${#v}
## stdout: 7
## N-I dash stdout: 13
## N-I mksh stdout: 13

#### String length with incomplete utf-8
for num_bytes in 0 1 2 3 4 5 6 7 8 9 10 11 12 13; do
  s=$(head -c $num_bytes $REPO_ROOT/spec/testdata/utf8-chars.txt)
  echo ${#s}
done 2> $TMP/err.txt

grep 'warning:' $TMP/err.txt
true  # exit 0

## STDOUT:
0
1
2
-1
3
4
-1
-1
5
6
-1
-1
-1
7
[ stdin ]:3: warning: UTF-8 Error: Truncated Bytes at byte index 2 in string of length 3
[ stdin ]:3: warning: UTF-8 Error: Truncated Bytes at byte index 5 in string of length 6
[ stdin ]:3: warning: UTF-8 Error: Truncated Bytes at byte index 5 in string of length 7
[ stdin ]:3: warning: UTF-8 Error: Truncated Bytes at byte index 9 in string of length 10
[ stdin ]:3: warning: UTF-8 Error: Truncated Bytes at byte index 9 in string of length 11
[ stdin ]:3: warning: UTF-8 Error: Truncated Bytes at byte index 9 in string of length 12
## END
# zsh behavior actually matches bash!
## BUG bash/zsh stderr-json: ""
## BUG bash/zsh STDOUT:
0
1
2
3
3
4
5
6
5
6
7
8
9
7
## END
## BUG dash/mksh stderr-json: ""
## N-I dash/mksh STDOUT:
0
1
2
3
4
5
6
7
8
9
10
11
12
13
## END

#### String length with invalid utf-8 continuation bytes
for num_bytes in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14; do
  s=$(head -c $num_bytes $REPO_ROOT/spec/testdata/utf8-chars.txt)$(echo -e "\xFF")
  echo ${#s}
done 2> $TMP/err.txt

grep 'warning:' $TMP/err.txt
true

## STDOUT:
-1
-1
-1
-1
-1
-1
-1
-1
-1
-1
-1
-1
-1
-1
-1
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 0 in string of length 1
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 1 in string of length 2
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 2 in string of length 3
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 2 in string of length 4
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 4 in string of length 5
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 5 in string of length 6
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 5 in string of length 7
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 5 in string of length 8
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 8 in string of length 9
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 9 in string of length 10
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 9 in string of length 11
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 9 in string of length 12
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 9 in string of length 13
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 13 in string of length 14
[ stdin ]:3: warning: UTF-8 Error: Bad Encoding at byte index 13 in string of length 14
## END
## BUG bash/zsh stderr-json: ""
## BUG bash/zsh STDOUT:
1
2
3
4
4
5
6
7
6
7
8
9
10
8
8
## N-I dash stderr-json: ""
## N-I dash STDOUT:
7
8
9
10
11
12
13
14
15
16
17
18
19
20
20
## END
## N-I mksh stderr-json: ""
## N-I mksh STDOUT:
1
2
3
4
5
6
7
8
9
10
11
12
13
14
14
## END

#### Length of undefined variable
echo ${#undef}
## stdout: 0

#### Length of undefined variable with nounset
set -o nounset
echo ${#undef}
## status: 1
## OK dash status: 2

#### Length operator can't be followed by test operator
echo ${#x-default}

x=''
echo ${#x-default}

x='foo'
echo ${#x-default}

## status: 2
## OK bash/mksh status: 1
## stdout-json: ""
## BUG zsh status: 0
## BUG zsh STDOUT:
7
0
3
## END
## BUG dash status: 0
## BUG dash STDOUT:
0
0
3
## END

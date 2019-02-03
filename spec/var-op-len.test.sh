#!/usr/bin/env bash
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
v=$(cat spec/testdata/utf8-chars.txt)
echo ${#v}
## stdout: 7
## N-I dash stdout: 13
## N-I mksh stdout: 13

#### String length with incomplete utf-8
for num_bytes in 0 1 2 3 4 5 6 7 8 9 10 11 12 13; do
  s=$(head -c $num_bytes spec/testdata/utf8-chars.txt)
  echo ${#s}
done
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
## END
## STDERR:
osh warning: Incomplete UTF-8 character
osh warning: Incomplete UTF-8 character
osh warning: Incomplete UTF-8 character
osh warning: Incomplete UTF-8 character
osh warning: Incomplete UTF-8 character
osh warning: Incomplete UTF-8 character
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
  s=$(head -c $num_bytes spec/testdata/utf8-chars.txt)$(echo -e "\xFF")
  echo ${#s}
done
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
## END
## STDERR:
osh warning: Invalid start of UTF-8 character
osh warning: Invalid start of UTF-8 character
osh warning: Invalid start of UTF-8 character
osh warning: Invalid UTF-8 continuation byte
osh warning: Invalid start of UTF-8 character
osh warning: Invalid start of UTF-8 character
osh warning: Invalid UTF-8 continuation byte
osh warning: Invalid UTF-8 continuation byte
osh warning: Invalid start of UTF-8 character
osh warning: Invalid start of UTF-8 character
osh warning: Invalid UTF-8 continuation byte
osh warning: Invalid UTF-8 continuation byte
osh warning: Invalid UTF-8 continuation byte
osh warning: Invalid start of UTF-8 character
osh warning: Invalid start of UTF-8 character
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


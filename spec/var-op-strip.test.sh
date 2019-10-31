#!/usr/bin/env bash

#### Remove const suffix
v=abcd
echo ${v%d} ${v%%cd}
## stdout: abc ab

#### Remove const prefix
v=abcd
echo ${v#a} ${v##ab}
## stdout: bcd cd

#### Remove const suffix is vectorized on user array
a=(1a 2a 3a)
argv.py ${a[@]%a}
## stdout: ['1', '2', '3']
## status: 0
## N-I dash/mksh/ash stdout-json: ""
## N-I dash/ash status: 2
## N-I mksh status: 1

#### Remove const suffix is vectorized on $@ array
set -- 1a 2a 3a
argv.py ${@%a}
## stdout: ['1', '2', '3']
## status: 0
## N-I dash/ash stdout: ['1a', '2a', '3']
## N-I dash/ash status: 0
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### Remove const suffix from undefined
echo ${undef%suffix}
## stdout:

#### Remove shortest glob suffix
v=aabbccdd
echo ${v%c*}
## stdout: aabbc

#### Remove longest glob suffix
v=aabbccdd
echo ${v%%c*}
## stdout: aabb

#### Remove shortest glob prefix
v=aabbccdd
echo ${v#*b}
## stdout: bccdd

#### Remove longest glob prefix
v=aabbccdd
echo ${v##*b}
## stdout: ccdd

#### Strip char class
v=abc
echo ${v%[[:alpha:]]}
## stdout: ab
## N-I mksh stdout: abc

#### Strip unicode prefix
# NOTE: LANG is set to utf-8.
v='μ-'
echo ${v#?}  # ? is a glob that stands for one character
echo ${v##?}
v='-μ'
echo ${v%?}  # ? is a glob that stands for one character
echo ${v%%?}
## STDOUT:
-
-
-
-
## BUG dash/mksh/ash stdout-repr: '\xbc-\n\xbc-\n-\xce\n-\xce\n'
## BUG zsh stdout-repr: '\n\n\n\n'

#### Bug fix: Test that you can remove everything with glob
s='--x--'
argv.py "${s%%-*}" "${s%-*}" "${s#*-}" "${s##*-}"
## STDOUT:
['', '--x-', '-x--', '']
## END

#### Test that you can remove everything with const
s='abcd'
argv.py "${s%%abcd}" "${s%abcd}" "${s#abcd}" "${s##abcd}"
# failure case:
argv.py "${s%%abcde}" "${s%abcde}" "${s#abcde}" "${s##abcde}"
## STDOUT:
['', '', '', '']
['abcd', 'abcd', 'abcd', 'abcd']
## END

#### Prepend using replacement of #
# This case was found in Kubernetes and others
array=(aa bb '')
argv.py ${array[@]/#/prefix-}
## STDOUT:
['prefix-aa', 'prefix-bb', 'prefix-']
## END
## N-I dash/ash status: 2
## N-I dash/ash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### Append using replacement of %
array=(aa bb '')
argv.py ${array[@]/%/-suffix}
## STDOUT:
['aa-suffix', 'bb-suffix', '-suffix']
## END
## N-I dash/ash status: 2
## N-I dash/ash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### strip unquoted and quoted [
# I guess dash and mksh treat unquoted [ as an invalid glob?
var='[foo]'
echo ${var#[}
echo ${var#"["}
echo "${var#[}"
echo "${var#"["}"
## STDOUT:
foo]
foo]
foo]
foo]
## END
## OK dash/mksh STDOUT:
[foo]
foo]
[foo]
foo]
## END
## BUG zsh stdout-json: ""
## BUG zsh status: 1

#### strip unquoted and quoted []
# LooksLikeGlob('[]') is true
# I guess dash, mksh, and zsh treat unquoted [ as an invalid glob?
var='[]foo[]'
echo ${var#[]}
echo ${var#"[]"}
echo "${var#[]}"
echo "${var#"[]"}"
## STDOUT:
foo[]
foo[]
foo[]
foo[]
## END
## OK dash/mksh/zsh STDOUT:
[]foo[]
foo[]
[]foo[]
foo[]
## END

#### strip unquoted and quoted ?
var='[foo]'
echo ${var#?}
echo ${var#"?"}
echo "${var#?}"
echo "${var#"?"}"
## STDOUT:
foo]
[foo]
foo]
[foo]
## END

#### strip unquoted and quoted [a]
var='[a]foo[]'
echo ${var#[a]}
echo ${var#"[a]"}
echo "${var#[a]}"
echo "${var#"[a]"}"
## STDOUT:
[a]foo[]
foo[]
[a]foo[]
foo[]
## END

#### Nested % and # operators (bug reported by Crestwave)
var=$'\n'
argv.py "${var#?}"
argv.py "${var%''}"
argv.py "${var%"${var#?}"}"
var='a'
argv.py "${var#?}"
argv.py "${var%''}"
argv.py "${var%"${var#?}"}"
## STDOUT:
['']
['\n']
['\n']
['']
['a']
['a']
## END
## N-I dash STDOUT:
['\\n']
['$\\n']
['$']
['']
['a']
['a']
## END

#### strip * (bug regression)
x=abc
argv.py "${x#*}"
argv.py "${x##*}"
argv.py "${x%*}"
argv.py "${x%%*}"
## STDOUT:
['abc']
['']
['abc']
['']
## END
## BUG zsh STDOUT:
['abc']
['']
['ab']
['']
## END

#### strip ?
x=abc
argv.py "${x#?}"
argv.py "${x##?}"
argv.py "${x%?}"
argv.py "${x%%?}"
## STDOUT:
['bc']
['bc']
['ab']
['ab']
## END

#### strip all
x=abc
argv.py "${x#abc}"
argv.py "${x##abc}"
argv.py "${x%abc}"
argv.py "${x%%abc}"
## STDOUT:
['']
['']
['']
['']
## END

#### strip none
x=abc
argv.py "${x#}"
argv.py "${x##}"
argv.py "${x%}"
argv.py "${x%%}"
## STDOUT:
['abc']
['abc']
['abc']
['abc']
## END

#### strip all unicode
x=μabcμ
echo "${x#?abc?}"
echo "${x##?abc?}"
echo "${x%?abc?}"
echo "${x%%?abc?}"
## STDOUT:




## BUG dash/mksh/ash STDOUT:
μabcμ
μabcμ
μabcμ
μabcμ
## END

#### strip none unicode
x=μabcμ
argv.py "${x#}"
argv.py "${x##}"
argv.py "${x%}"
argv.py "${x%%}"
## STDOUT:
['\xce\xbcabc\xce\xbc']
['\xce\xbcabc\xce\xbc']
['\xce\xbcabc\xce\xbc']
['\xce\xbcabc\xce\xbc']
## END

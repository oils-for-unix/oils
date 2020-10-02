#!/usr/bin/env bash
#
# Adapted from gold/echo-e.sh, which was adapted from spec/builtin-io.test.sh.

echo $'foo\tbar\n'

echo $'foo\tbar\n\
baz'

echo $'\\'
echo $'abc\ndef\n'
echo $'\a\b\d\e\f'
echo $'\n\r\t\v'
# Doesn't pass because Python can have NUL embedded in strings!
#echo $'ab\0cd' | od -A n -c | sed 's/ \+/ /g'
echo $'abcd\x65f'
echo $'abcd\044e'
echo $'abcd\u0065f'
echo $'abcd\U00000065f'

# NOTE: $'\377' is echo -e '\0377', with leading 0
echo $'\3777' | od -A n -t x1 | sed 's/ \+/ /g'
echo $'\4010' | od -A n -t x1 | sed 's/ \+/ /g'
echo $'\777' | od -A n -t x1 | sed 's/ \+/ /g'

# This wraps to \0, so it's not used.
#echo $'\4000' | od -A n -t x1 | sed 's/ \+/ /g'

echo $'abcd\x6' | od -A n -c | sed 's/ \+/ /g'
echo $'\x' $'\xg' | od -A n -c | sed 's/ \+/ /g'
echo $'abcd\04' | od -A n -c | sed 's/ \+/ /g'
echo $'abcd\u006' | od -A n -c | sed 's/ \+/ /g'
echo $'\u6' | od -A n -c | sed 's/ \+/ /g'
#echo $'\0' '\1' '\8' | od -A n -c | sed 's/ \+/ /g'

echo $'\1 \11 \11 \111' | od -A n -c | sed 's/ \+/ /g'

echo $'foo
bar'

echo $'foo\
bar'

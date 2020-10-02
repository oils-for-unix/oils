#!/usr/bin/env bash
#
# Semi-automatically extracted like this:
#
# grep ^echo spec/builtin-io.test.sh.
#
# For converting to gold/dollar-sq.sh.

echo -e '\\'
echo -en 'abc\ndef\n'
echo -ez 'abc\n'
echo -e '\a\b\d\e\f'
echo -e '\n\r\t\v'
echo -e 'ab\0cd'
echo -e xy  'ab\cde'  'ab\cde'
echo -e 'abcd\x65f'
echo -e 'abcd\044e'
echo -e 'abcd\u0065f'
echo -e 'abcd\U00000065f'
echo -e '_\u03bc_'
echo -e '_\U000003bc_'
echo -en '\03777' | od -A n -t x1 | sed 's/ \+/ /g'
echo -en '\04000' | od -A n -t x1 | sed 's/ \+/ /g'
echo -e '\0777' | od -A n -t x1 | sed 's/ \+/ /g'
echo -en 'abcd\x6' | od -A n -c | sed 's/ \+/ /g'
echo -e '\x' '\xg' | od -A n -c | sed 's/ \+/ /g'
echo -e 'abcd\04' | od -A n -c | sed 's/ \+/ /g'
echo -en 'abcd\u006' | od -A n -c | sed 's/ \+/ /g'
echo -e '\u6' | od -A n -c | sed 's/ \+/ /g'
echo -e '\0' '\1' '\8' | od -A n -c | sed 's/ \+/ /g'

echo -e 'foo
bar'

echo -e 'foo\
bar'

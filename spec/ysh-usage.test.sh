## our_shell: ysh

#### ysh usage

set +o errexit

$SH --location-str foo.hay --location-start-line 42 -c 'echo ()' 2>err.txt

cat err.txt | grep -o -- '-- foo.hay:42: Unexpected'


# common idiom is to use -- to say it came from a file
$SH --location-str '[ stdin ]' --location-start-line 10 -c 'echo "line 10";
echo ()' 2>err.txt

cat err.txt | fgrep -o -- '-- [ stdin ]:11: Unexpected'

## STDOUT:
-- foo.hay:42: Unexpected
line 10
-- [ stdin ]:11: Unexpected
## END

#### --debug-file
$SH --debug-file $TMP/debug.txt -c 'true'
grep 'Oils started with' $TMP/debug.txt >/dev/null && echo yes
## stdout: yes

#### Filename quoting

echo '(BAD' > no-quoting
echo '(BAD' > 'with spaces.sh'
echo '(BAD' > $'bad \xff'

write -n '' > err.txt

$SH no-quoting 2>>err.txt || true
$SH 'with spaces.sh' 2>>err.txt || true
$SH $'bad \xff' 2>>err.txt || true

egrep --only-matching '^.*:1' err.txt

## STDOUT:
no-quoting:1
"with spaces.sh":1
b'bad \yff':1
## END


#### shopt --set verbose_errexit

try {
  $SH -c '/bin/false' 2>on.txt
}

try {
  $SH +o verbose_errexit -c '/bin/false' 2>off.txt
}

wc -l on.txt off.txt
#echo
#cat on.txt off.txt

## STDOUT:
 3 on.txt
 0 off.txt
 3 total
## END

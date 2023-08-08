## our_shell: ysh
## oils_failures_allowed: 1

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

#### help shows 'ysh-chapters' topic

# doesn't show ANSI text unless TTY
help | grep ysh-chapters

echo status=$?

## STDOUT:
TODO fix dev-minimal ~~~ ysh-chapters ~~~
status=0
## END

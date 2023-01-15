#! /bin/sh

# From https://github.com/oilshell/oil/issues/1449

set -e

nargs () {
    n_args=$#
    return 0
}

check () {
    if [ "$1" = "$2" ]; then
        printf 'ok: %s\n' "$3"
    else
        printf 'FAIL: %s: got "%s" expected "%s"\n' "$3" "$1" "$2"
        status=1
    fi
}

a="a b"

nargs $a
check $n_args 2 'nargs $a'

nargs "$a"
check $n_args 1 'nargs "$a"'

nargs "$a" $a
check $n_args 3 'nargs "$a" $a'

n_args=`nargs "$a"; echo $n_args`
check $n_args 1 '`nargs "$a"`'

n_args=`nargs "$a" $a; echo $n_args`
check $n_args 3 '`nargs "$a" $a`'

eval "nargs \"$a\""
check $n_args 1 'eval "nargs \"$a\""'

eval "nargs \"$a\" $a"
check $n_args 3 'eval "nargs \"$a\" $a"'

n_args=`eval "nargs \"$a\""; echo $n_args`
check $n_args 1 'eval "nargs \"$a\""'

n_args=`eval "nargs \"$a\" $a"; echo $n_args`
check $n_args 3 'eval "nargs \"$a\" $a"'

exit $status

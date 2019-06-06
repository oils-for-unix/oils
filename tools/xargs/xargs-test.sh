#!/bin/sh

cd "$(realpath "$(dirname "$0")")"

mkdir -p _tmp/

if [ $# -eq 0 ]
then set -- "$PWD"/testdata/*/
fi

eval 'xargs_py() {' "$(realpath ./xargs.py)" '"$@";' '}'

for test
do
	args="$test/args"
	stdin="$test/stdin"
	stdout="_tmp/$(basename "$test")_stdout"
	stderr="_tmp/$(basename "$test")_stderr"
	eval xargs $(cat "$args") <"$stdin" >"${stdout}_expected" 2>/dev/null &
	eval xargs_py $(cat "$args") <"$test/stdin" >"${stdout}_actual" 2>"$stderr"
	rc_actual=$?
	wait %1
	rc_expected=$?
	if ! cmp -s "${stdout}_expected" "${stdout}_actual"
	then
		echo "!!! $(basename "$test") failed: files differ"
		echo "--- EXPECTED ---"
		cat "${stdout}_expected"
		echo "---- ACTUAL ----"
		cat "${stdout}_actual"
		echo "----------------"
		cat "$stderr"
	elif [ $rc_expected != $rc_actual ]
	then
		echo "!!! $(basename "$test") failed: rcs differ"
		echo "EXPECTED=$rc_expected ACTUAL=$rc_actual"
	else
		echo "    $(basename "$test") ok"
	fi
done

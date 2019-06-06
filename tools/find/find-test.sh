#!/bin/sh

set -e

cd "$(realpath "$(dirname "$0")")"
BASE="$PWD/../.."
export PYTHONPATH="$BASE:$BASE/vendor"

lorem_ipsum() {
	echo "Lorem ipsum dolor sit amet, consectetur adipisici elit"
}
setup_testdir() (
	mkdir -p "$1"
	cd "$1"

	touch emptyfile.txt
	ln -s emptyfile.txt softlink.ln
	ln    emptyfile.txt hardlink.ln

	mkdir dir_a dir_b dir_c

	for d in ./dir_*
	do
		for i in $(seq 4)
		do lorem_ipsum >"${d}/plainfile_${i}.txt"
		done
	done

	mkdir dir_p
	for p in R W X RW RX WX RWX
	do touch dir_p/$p
	done
	for f in ./dir_p/*
	do
		chmod 000 "$f"
		case $f in
		*/*X*)	chmod +x "$f"
		esac
		case $f in
		*/*W*)	chmod +w "$f"
		esac
		case $f in
		*/*R*)	chmod +r "$f"
		esac
	done
)

testdir="_tmp/find-testdir"
test -d "$testdir" || setup_testdir "$testdir"

if [ $# -eq 0 ]
then set -- "$PWD"/testdata/*
fi

eval 'find_py() (' "cd $PWD/../..;" "$(realpath ./find.py)" '"$@";' ')'

set +e

for test
do
	stdout="_tmp/$(basename "$test")_stdout"
	stderr="_tmp/$(basename "$test")_stderr"
	eval find "$(realpath "$testdir")" $(cat "$test") 2>/dev/null | sort >"${stdout}_expected" &
	eval find_py "$(realpath "$testdir")" $(cat "$test") 2>"$stderr"| sort >"${stdout}_actual"
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

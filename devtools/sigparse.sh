#!/bin/bash
#
# Parse signal format in /proc.
#
# Copied from:
# https://unix.stackexchange.com/questions/85364/how-can-i-check-what-signals-a-process-is-listening-to
#
# Usage:
#   ./sigparse.sh PID

sigparse () {
    i=0
    # bits="$(printf "16i 2o %X p" "0x$1" | dc)" # variant for busybox
    bits="$(printf "ibase=16; obase=2; %X\n" "0x$1" | bc)"
    while [ -n "$bits" ] ; do
        i="$(expr "$i" + 1)"
        case "$bits" in
            *1) printf " %s(%s)" "$(kill -l "$i")" "$i" ;;
        esac
        bits="${bits%?}"
    done
}

grep "^Sig...:" "/proc/$1/status" | while read a b ; do
        printf "%s%s\n" "$a" "$(sigparse "$b")"
    done # | fmt -t  # uncomment for pretty-printing

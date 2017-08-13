#!/bin/bash
#
# Nice examples from blog post feedback.
#
# Usage:
#   ./hard-coded-descriptors.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# https://www.reddit.com/r/bash/comments/6td8j2/avoid_directly_manipulating_file_descriptors_in/

interactive-stdin() {
  local path=$0  # This script
	while read line <&"$fd" ; do
    echo "[$line]"
    read -p "Continue? " ans 
    [[ "$ans" != yes ]] && exit 1
	done {fd}< $path
}

# https://www.reddit.com/r/oilshell/comments/6tch5v/avoid_directly_manipulating_file_descriptors_in/

log-dates() {
  exec {fd}> >(while IFS= read -r line; do printf "[%s] %s\n" "$(date)" "$line"; done)
  echo "Hello" >&"$fd"
  echo "Goodbye" >&"$fd"
}

tee-like() {
  local log=_tmp/tee-like.txt

  >$log  # truncate

  exec {fd}> >(while IFS= read -r line; do printf "%s\n" "$line"; printf "%s\n" "$line" >&3; done 3>>"$log")
  echo "Hello" >&"$fd"
  echo "Goodbye" >&"$fd"

  echo
  echo "Contents of $log:"
  cat $log
}

# Hm this one isn't working yet
pipe-stderr() {
  local log=_tmp/pipe-stderr.log
  set +o errexit

  ls -l /etc/passwd not_a_file 3>&1 1>&2 2>&3 \
    | awk '{print "ERROR:" $0}' >$log

  # Another idiom, this seems wrong because of 3>&-
  exec 3>&1
  ls -l /etc/passwd 'not_a_file_2' 2>&1 >&3 3>&- \
    | awk '{print "ERROR:" $0}' >>$log
  exec 3>&-

  echo
  echo "Contents of $log:"
  cat $log
}

_zip() {
  ( # use a subshell to ensure the FD changes don't affect the caller
  exec 4<"$1" 5<"$2"
  while IFS="" read -u 4 a && read -u 5 b; do
    printf "%s %s\n" "$a" "$b"
  done
  )
}

zip-demo() {
  seq 1 5 > _tmp/left.txt
  seq 5 10 > _tmp/right.txt
  _zip _tmp/{left,right}.txt 
}

"$@"

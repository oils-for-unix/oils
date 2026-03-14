#!/usr/bin/env bash
#
# Report on wedge sizes for CI
#
# Usage:
#   deps/wedge-report.sh <function name>
#
# Examples:
#   deps/wedge-report.sh show

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

commas() {
  # Wow I didn't know this :a trick
  #
  # OK this is a label and a loop, which makes sense.  You can't do it with
  # pure regex.
  #
  # https://shallowsky.com/blog/linux/cmdline/sed-improve-comma-insertion.html
  # https://shallowsky.com/blog/linux/cmdline/sed-improve-comma-insertion.html
  sed ':a;s/\b\([0-9]\+\)\([0-9]\{3\}\)\b/\1,\2/;ta'   
}

wedge-sizes() {
  local tmp=_tmp/wedge-sizes.txt

  # -b is --bytes, but use short flag for busybox compat
  du -s -b ../oils.DEPS/wedge/*/* | awk '
    { print $0  # print the line
      total_bytes += $1  # accumulate
    }
END { print total_bytes " TOTAL" }
' > $tmp
  
  # printf justifies du output
  cat $tmp | commas | xargs -n 2 printf '%15s  %s\n'
  echo

  #du -s --si /wedge/*/*/* ~/wedge/*/*/* 
  #echo
}

show() {
  # 4 levels deep shows the package
  if command -v tree > /dev/null; then
    tree -L 4 ../oils.DEPS
    echo
  fi

  wedge-sizes

  local tmp=_tmp/wedge-manifest.txt

  echo 'Biggest files'
  if ! find ../oils.DEPS/wedge -type f -a -printf '%10s %P\n' > $tmp; then
    # busybox find doesn't have -printf
    echo 'find -printf failed'
    return
  fi

  set +o errexit  # ignore SIGPIPE
  sort -n --reverse $tmp | head -n 20 | commas
  set -o errexit

  echo

  # Show the most common file extensions
  #
  # I feel like we should be able to get rid of .a files?  That's 92 MB, second
  # most common
  #
  # There are also duplicate .a files for Python -- should look at how distros
  # get rid of those

  cat $tmp | python3 -c '
import os, sys, collections

bytes = collections.Counter()
files = collections.Counter()

for line in sys.stdin:
  size, path = line.split(None, 1)
  path = path.strip()  # remove newline
  _, ext = os.path.splitext(path)
  size = int(size)

  bytes[ext] += size
  files[ext] += 1

#print(bytes)
#print(files)

n = 20

print("Most common file types")
for ext, count in files.most_common()[:n]:
  print("%10d  %s" % (count, ext))

print()

print("Total bytes by file type")
for ext, total_bytes in bytes.most_common()[:n]:
  print("%10d  %s" % (total_bytes, ext))
' | commas
}

task-five "$@"

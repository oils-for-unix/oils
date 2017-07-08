#!/usr/bin/env bash
#
# Test awk vs Python speed.
#
# On this hash table benchmark, Python is maybe 10% slower than gawk.  mawk is
# twice is fast as gawk (and bwk).
#
# Python has much more functionality, so it's not exactly a fair comparison,
# but it's instructive.
#
# Update: simply adding tolower() makes gawk much slower than Python (555 ms
# vs. 280 ms), and mawk is still much faster at 138 ms.
#
# Mawk is known to be fast?  Faster than Java on this benchmark.
# https://brenocon.com/blog/2009/09/dont-mawk-awk-the-fastest-and-most-elegant-big-data-munging-language/
#
# Usage:
#   ./awk-python.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly FILES=(../*.sh ../*/*.sh ../*.py ../*/*.py ../*/*/*.py)

# Test out hash table implementations
# mawk is faster: 77ms vs 155ms for 10 iterations.
test-awk() {
  for awk in gawk mawk ~/git/bwk/bwk; do
    echo ---
    echo $awk
    echo ---
    time for i in {1..10}; do
      $awk '
      { 
        line = tolower($0)
        num_lines += 1

        # NOTE: gawk has length(); mawk does not
        if (!(line in unique)) {
          num_unique += 1
        }
        unique[line] += 1
      }
      END {
        print "unique lines: " num_unique
        print "total lines: " num_lines
      }
      ' "${FILES[@]}"

    done
  done
}

# Python VM is slower: 160-170 ms.  Oops.
#
# Well Python has more general dictionaries -- they take more than strings.
test-python() {
  time for i in {1..10}; do
    python -S -c '
import collections
import sys

num_lines = 0
num_unique = 0
unique = collections.defaultdict(int)

for path in sys.argv[1:]:
  with open(path) as f:
    for line in f:
      line = line.lower()
      num_lines += 1

      if line not in unique:
        num_unique += 1
      unique[line] += 1

print "unique lines: ", num_unique
print "total lines: ", num_lines
      ' "${FILES[@]}"

  done
}

# Only 10-30 ms.  We are doing real work.
test-wc() {
  time for i in {1..10}; do
    cat "${FILES[@]}" | wc -c
  done
}

files() {
  echo "${FILES[@]}"
  echo "${#FILES[@]} files"
}

"$@"

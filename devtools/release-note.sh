#!/bin/bash
#
# Usage:
#   devtools/release-note.sh <function name>
#
# Example:
#   $0 fetch-issues
#   $0 write-template

set -o nounset
set -o pipefail
set -o errexit

source devtools/release-version.sh  # for escape-segements

readonly OIL_VERSION=$(head -n 1 oil-version.txt)
readonly PREV_VERSION='0.8.pre2'

# adapted from release-version.sh
_git-changelog-body() {
  local prev_branch=$1
  local cur_branch=$2
  shift 2

  # - a trick for HTML escaping (avoid XSS): surround %s with unlikely bytes,
  #   \x00 and \x01.  Then pipe Python to escape.
  # --reverse makes it go in forward chronlogical order.

  # %x00 generates the byte \x00
  local format='<tr>
    <td><a class="checksum"
           href="https://github.com/oilshell/oil/commit/%H">%h</a>
    </td>
    <td>%x00%an%x01</td>
    <td class="subject">%x00%s%x01</td>
  </tr>'
  git log \
    $prev_branch..$cur_branch \
    --reverse \
    --pretty="format:$format" \
    --date=short \
    "$@" \
  | escape-segments
}

contrib-commit-table() {
  # show commits not made by me
  _git-changelog-body release/$PREV_VERSION release/$OIL_VERSION \
    --author 'Andy Chu' --invert-grep
}

fetch-issues() {
  local url='https://api.github.com/repos/oilshell/oil/issues?labels=pending-release'
  curl "$url" > _tmp/issues.json
}

issues-table() {
  cat _tmp/issues.json | devtools/github_issues.py
}

write-template() {
  local out=../oilshell.org/blog/2020/03/_release-$OIL_VERSION.md
  print-template > $out
  echo "Wrote $out"
}

print-template() {
  local metric_prev=${1:-$PREV_VERSION}

  cat <<EOF
---
title: Release of Oil $OIL_VERSION
date: $(date +%Y/%m/%d)
tags: oil-release
comments_url: TODO
published: no
---

<!-- copied from web/changelog.css -->
<style>
.checksum {
  font-family: monospace;
}
.issue-num {
  font-family: monospace;
  width: 3em;
}
</style>

This is the latest version of Oil, a bash-compatible shell:

- [Oil version $OIL_VERSION][release-index]

Please try it on your shell scripts and [report bugs][github-bugs]!  To build
and run it, follow the instructions in [INSTALL.txt][].  The wiki has more tips
on [How To Test OSH](\$wiki).

If you're new to the project, see [Why Create a New Shell?][why-oil] and the
[2019 FAQ](../06/17.html).

[INSTALL.txt]: /release/$OIL_VERSION/doc/INSTALL.html
[github-bugs]: https://github.com/oilshell/oil/issues
[why-oil]: ../../2018/01/28.html
[release-index]: /release/$OIL_VERSION/

[oilshell.zulipchat.com]: http://oilshell.zulipchat.com/

<div id="toc">
</div> 

I'm trying something different this release.  These release notes are
semi-automated with a shell script!  See the [last
post](../02/good-parts-sketch.html) in #[shell-the-good-parts](\$blog-tag).

## Closed Issues

<table>
EOF

  issues-table 

  cat <<EOF
</table>

## Commit Log

Here are the commits from other contributors.  You can also view the [full
changelog][changelog].

[changelog]: /release/$OIL_VERSION/changelog.html

<table>
EOF

  contrib-commit-table

  cat <<EOF
</table>

## Documentation Updated

- [Known Differences](/release/$OIL_VERSION/doc/known-differences.html)
- [Interpreter State](/release/$OIL_VERSION/doc/interpreter-state.html) - still
	a draft.

### Wiki Pages

- [How Interactive Shells Work](https://github.com/oilshell/oil/wiki/How-Interactive-Shells-Work)


## What's Next?

Here are some notable Open Issues

- [Provide APIs to allow users to write their own line editor / interactive
interface](\$issue:663)

## Appendix: Metrics for the $OIL_VERSION Release

Let's compare this release with the previous one, version [$metric_prev](/release/$metric_prev).

OSH spec tests:

[spec-test]: \$xref:spec-test

- [OSH spec tests for $metric_prev](//www.oilshell.org/release/$metric_prev/test/spec.wwz/osh.html): **1260** tests, **1116** passing, **104** failing
- [OSH spec tests for $OIL_VERSION](//www.oilshell.org/release/$OIL_VERSION/test/spec.wwz/osh.html): **1393** tests, **1230** passing, **78** failing

Oil spec tests:

- [Oil spec tests for $metric_prev](//www.oilshell.org/release/$metric_prev/test/spec.wwz/oil.html): **1260** tests, **1116** passing, **104** failing
- [Oil spec tests for $OIL_VERSION](//www.oilshell.org/release/$OIL_VERSION/test/spec.wwz/oil.html): **1393** tests, **1230** passing, **78** failing

We have X significant lines of code:

- [cloc for $metric_prev](//www.oilshell.org/release/$metric_prev/metrics.wwz/line-counts/osh-cloc.txt):
  **11,041** lines of Python and C, **~200** lines of ASDL (excluding
  testdata).
- [cloc for $OIL_VERSION](//www.oilshell.org/release/$OIL_VERSION/metrics.wwz/line-counts/osh-cloc.txt): **12,447** lines of Python and C, **239** lines of ASDL

And X new lines of physical code:

- [src for
  $metric_prev](//www.oilshell.org/release/$metric_prev/metrics.wwz/line-counts/src.txt):
  **20,553** lines of Python
- [src for $OIL_VERSION](//www.oilshell.org/release/$OIL_VERSION/metrics.wwz/line-counts/src.txt): **23,343** lines of Python

### Benchmarks

- [Parser Performance for
  $metric_prev](//www.oilshell.org/release/$metric_prev/benchmarks.wwz/osh-parser/):
  X lines/ms and X lines/ms
- [Parser Performance for
$OIL_VERSION](//www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/osh-parser/): Y lines/ms and Y lines/ms

Runtime:

- [Runtime Performance for
  $metric_prev](//www.oilshell.org/release/$metric_prev/benchmarks.wwz/osh-runtime/):
- [Runtime Performance for
$OIL_VERSION](//www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/osh-runtime/):

### Native Code Metrics

The lines of native code was reduced:

- [nativedeps for $metric_prev](//www.oilshell.org/release/$metric_prev/metrics.wwz/line-counts/nativedeps.txt): **133,291** lines
- [nativedeps for $OIL_VERSION](//www.oilshell.org/release/$OIL_VERSION/metrics.wwz/line-counts/nativedeps.txt): **130,403** lines

The binary size stayed almost the same:

- [ovm-build for
  $metric_prev](//www.oilshell.org/release/$metric_prev/benchmarks.wwz/ovm-build/):
  **1,042,936** bytes of native code (under GCC)
- [ovm-build for
  $OIL_VERSION](//www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/ovm-build/):
  **1,048,888** bytes of native code (under GCC)
EOF
}

"$@"

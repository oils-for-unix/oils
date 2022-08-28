#!/usr/bin/env bash
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
readonly PREV_VERSION='0.12.3'

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
    --author 'Andy Chu' --author 'andychu' --author 'Andy C' --invert-grep
}

fetch-issues() {
  local url='https://api.github.com/repos/oilshell/oil/issues?labels=pending-release'
  curl "$url" > _tmp/issues.json
}

issues-table() {
  cat _tmp/issues.json | devtools/services/github_issues.py
}

write-template() {
  local date=$(date +%Y/%m)
  local out=../oilshell.org/blog/$date/_release-$OIL_VERSION.md
  print-template > $out
  echo "Wrote $out"
}

print-template() {
  local metric_prev=${1:-$PREV_VERSION}

  cat <<EOF
---
title: Release of Oil $OIL_VERSION
date: $(date +%Y/%m/%d)
css_file: blog-bundle-v6.css
tags: oil-release
comments_url: TODO
published: no
---

This is the latest version of Oil, a Unix shell that's our upgrade path from
[bash][]:

[bash]: \$xref

<div class="attention">

[Oil version $OIL_VERSION][release-index] - Source tarballs and documentation.

</div>

To build and run it, follow the instructions in [INSTALL.txt][].  The wiki has
tips on [How To Test OSH](\$wiki).

If you're new to the project, see [Why Create a New Shell?][why-oil] and posts
tagged #[FAQ](\$blog-tag).

[INSTALL.txt]: /release/$OIL_VERSION/doc/INSTALL.html
[github-bugs]: https://github.com/oilshell/oil/issues
[why-oil]: ../../2021/01/why-a-new-shell.html
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

These metrics help me keep track of the project.  Let's compare this release
with the previous one, version [$metric_prev](/release/$metric_prev).

### Spec Tests

The spec test suites for both OSH and Oil continue to expand and turn green.

[spec-test]: \$xref:spec-test

- [OSH spec tests for $metric_prev](https://www.oilshell.org/release/$metric_prev/test/spec.wwz/survey/osh.html): **1994** tests, 
**1771** passing, **86** failing
- [OSH spec tests for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/test/spec.wwz/survey/osh.html): **2008** tests, **1783** passing, **87** failing

---

- [Oil spec tests for $metric_prev](https://www.oilshell.org/release/$metric_prev/test/spec.wwz/oil-language/oil.html): **404** tests, **375** passing, **29** failing
- [Oil spec tests for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/test/spec.wwz/oil-language/oil.html): **419** tests, **391** passing, **28** failing

### Source Code Size

Despite the new features, the code is still compact.  Significant lines:

- [cloc for $metric_prev](https://www.oilshell.org/release/$metric_prev/pub/metrics.wwz/line-counts/osh-cloc.txt):
  **19,318** lines of Python and C, **346** lines of ASDL
- [cloc for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/pub/metrics.wwz/line-counts/osh-cloc.txt):
  **19,408** lines of Python and C, **346** lines of ASDL

Physical lines:

- [overview for $metric_prev](https://www.oilshell.org/release/$metric_prev/pub/metrics.wwz/line-counts/overview.html):
  **36,899** in OSH and common libraries, **4,843** in Oil
- [overview for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/pub/metrics.wwz/line-counts/overview.html):
  **37,095** in OSH and common libraries, **4,871** in Oil


### Benchmarks

The [oil-native](\$xref) Parser performance hasn't changed:

- [Parser Performance for $metric_prev](https://www.oilshell.org/release/$metric_prev/benchmarks.wwz/osh-parser/): **8.7**
  thousand irefs per line
- [Parser Performance for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/osh-parser/): **8.7**
  thousand irefs per line

Runtime performance for the Python / "[OVM](\$xref)" build:

- [Runtime Performance for $metric_prev](https://www.oilshell.org/release/$metric_prev/benchmarks.wwz/osh-runtime/): **88.7** and **48.5** seconds running CPython's \`configure\`
- [Runtime Performance for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/osh-runtime/):
  **92.1** and **70.6** seconds running CPython's \`configure\`

### Native Code Metrics

I didn't work on the translation during this release, but we're not regressing:

- [OSH C++ spec tests for $metric_prev](https://www.oilshell.org/release/$metric_prev/test/spec.wwz/cpp/osh-summary.html): **1777** tests, **1627** pass in Python, **1487** pass in C++
- [OSH C++ spec tests for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/test/spec.wwz/cpp/osh-summary.html): **1786** tests, **1637** pass in Python, **1495** pass in C++.

The following deltas are proportional.  Generated source lines;

- [oil-cpp for $metric_prev](https://www.oilshell.org/release/$metric_prev/pub/metrics.wwz/line-counts/oil-cpp.txt): **93,239** lines of C++
- [oil-cpp for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/pub/metrics.wwz/line-counts/oil-cpp.txt): **93,566** lines of C++

Binary size:

- [ovm-build for $metric_prev](https://www.oilshell.org/release/$metric_prev/benchmarks.wwz/ovm-build/):
  **1,376,608** bytes of native code (under GCC)
- [ovm-build for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/ovm-build/):
  **1,388,960** bytes of native code (under GCC)

EOF
}

"$@"

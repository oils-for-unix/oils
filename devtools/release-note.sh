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

source build/dev-shell.sh  # PYTHONPATH
source devtools/release-version.sh  # for escape-segments

readonly OIL_VERSION=$(head -n 1 oil-version.txt)
readonly PREV_VERSION='0.16.0'

# adapted from release-version.sh
_git-changelog-body() {
  local commit=$1

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
    --reverse \
    --pretty="format:$format" \
    --date=short \
    -n 1 \
    $commit \
  | escape-segments
}

contrib-commit-table() {
  # Filter out my commits, then pass back to git log

  # 2023-07: Deoptimized due to git breakage
  # https://stackoverflow.com/questions/6889830/equivalence-of-git-log-exclude-author

  git log --format='%H %an' "release/$PREV_VERSION..release/$OIL_VERSION" |
    grep -v 'Andy C' |
    cut -d ' ' -f 1  |
    xargs -n 1 $0 _git-changelog-body

    #xargs -n 1 -- git log -n 1
}

fetch-issues() {
  local url='https://api.github.com/repos/oilshell/oil/issues?labels=pending-release'
  curl "$url" > _tmp/issues.json
}

issues-table() {
  cat _tmp/issues.json | devtools/services/github_issues.py
}

write-template() {
  ### New blog post

  local date=$(date +%Y/%m)
  local out=../oilshell.org/blog/$date/_release-$OIL_VERSION.md
  print-template > $out
  echo "Wrote $out"
}

preview-template() {
  local out=_tmp/release-note.html

  # This isn't right because it doesn't split the --- front matter
  # But good enough for now

  print-template | doctools/cmark.py > $out
  log "Wrote $out"
}

print-template() {
  local metric_prev=${1:-$PREV_VERSION}

  cat <<EOF
---
title: Oils $OIL_VERSION - Foo Foo
date: $(date +%Y/%m/%d)
css_file: blog-bundle-v6.css
body_css_class: width35
default_highlighter: oil-sh
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

[spec-test]: \$xref:spec-test

### Spec Tests

The Python reference implementation foo foo

- [OSH spec tests for $metric_prev](https://www.oilshell.org/release/$metric_prev/test/spec.wwz/survey/osh.html): **2023** tests, 
**1789** passing, **91** failing
- [OSH spec tests for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/test/spec.wwz/survey/osh.html): **2042** tests, **1814** passing, **89** failing

And the C++ translation foo foo

- [C++ spec tests for $metric_prev](https://www.oilshell.org/release/$metric_prev/test/spec.wwz/cpp/osh-summary.html) - **1684** of **1792** passing
- [C++ spec tests for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/test/spec.wwz/cpp/osh-summary.html) - **1801** of **1817** passing

---

YSH / Oil foo foo

- [Oil spec tests for $metric_prev](https://www.oilshell.org/release/$metric_prev/test/spec.wwz/oil-language/oil.html): **502** tests, **464** passing, **38** failing
- [Oil spec tests for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/test/spec.wwz/oil-language/oil.html): **506** tests, **466** passing, **40** failing


### Benchmarks

Bar Bar

- [Parser Performance for $metric_prev](https://www.oilshell.org/release/$metric_prev/benchmarks.wwz/osh-parser/): **21.8**
  thousand irefs per line
- [Parser Performance for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/osh-parser/): **26.0**
  thousand irefs per line

Foo Foo

- [Runtime Performance for $metric_prev](https://www.oilshell.org/release/$metric_prev/benchmarks.wwz/osh-runtime/): **68.7** and **56.9** seconds running CPython's \`configure\`
- [Runtime Performance for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/osh-runtime/):
  **35.2** and **22.5** seconds running CPython's \`configure\`
- [bash](\$xref): **26.8** and **16.2** seconds running CPython's \`configure\`


### Code Size

The executable spec foo foo 

Significant lines:

- [cloc for $metric_prev](https://www.oilshell.org/release/$metric_prev/pub/metrics.wwz/line-counts/osh-cloc.txt):
  **19,581** lines of Python and C, **355** lines of ASDL
- [cloc for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/pub/metrics.wwz/line-counts/osh-cloc.txt):
  **19,491** lines of Python and C, **363** lines of ASDL
  
Code in the \`oils-for-unix\` C++ tarball, much of which is generated:

- [oil-cpp for $metric_prev](https://www.oilshell.org/release/$metric_prev/pub/metrics.wwz/line-counts/oil-cpp.txt) - **86,985** lines
- [oil-cpp for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/pub/metrics.wwz/line-counts/oil-cpp.txt) - **90,682** lines

Compiled binary size:

- [ovm-build for $metric_prev](https://www.oilshell.org/release/$metric_prev/benchmarks.wwz/ovm-build/):
  **1.18 MB** of native code (under GCC)
- [ovm-build for $OIL_VERSION](https://www.oilshell.org/release/$OIL_VERSION/benchmarks.wwz/ovm-build/):
  **1.23 MB** of native code (under GCC)

&nbsp;

EOF
}

"$@"

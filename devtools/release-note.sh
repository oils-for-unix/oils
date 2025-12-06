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

readonly OILS_VERSION=$(head -n 1 oils-version.txt)
readonly PREV_VERSION='0.36.0'

if false; then  # replaced

# adapted from release-version.sh
_git-changelog-body() {
  local commit=$1

  # - a trick for HTML escaping (avoid XSS): surround %s with unlikely bytes,
  #   \x00 and \x01.  Then pipe Python to escape.
  # --reverse makes it go in forward chronlogical order.

  # %x00 generates the byte \x00
  local format='<tr>
    <td><a class="checksum"
           href="https://github.com/oils-for-unix/oils/commit/%H">%h</a>
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

  git log --format='%H %an' "release/$PREV_VERSION..release/$OILS_VERSION" |
    grep -v 'Andy C' |
    cut -d ' ' -f 1  |
    xargs -n 1 $0 _git-changelog-body

    #xargs -n 1 -- git log -n 1
}
fi

fetch-issues() {
  local label=${1:-pending-release}
  local url="https://api.github.com/repos/oils-for-unix/oils/issues?labels=$label"
  curl "$url" > _tmp/issues.json
}

issues-table() {
  cat _tmp/issues.json | devtools/services/github_issues.py
}

readonly DATE_DIR=$(date +%Y/%m)
readonly BLOG_DIR="../oils.pub/blog/$DATE_DIR"

write-template() {
  ### New blog post

  local out=$BLOG_DIR/_release-$OILS_VERSION.md
  print-template > $out
  echo "Wrote $out"
}

write-zulip-thread() {
  local bot_email=$1
  local bot_api_key=$2
  local version=${3:-$OILS_VERSION}
  
  local out=$BLOG_DIR/release-thread-$version.txt
  devtools/services/zulip.sh print-thread \
    "$bot_email" "$bot_api_key" oil-dev "Oils $version Release" \
    | tee $out

  echo
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
title: Oils $OILS_VERSION - Foo Foo
date: $(date +%Y/%m/%d)
css_file: blog-bundle-v7.css
body_css_class: width40
default_highlighter: oils-sh
tags: oils-release
comments_url: TODO
published: no
---

<style>
  /* shortlog style adapted from devtools/release-version.sh */
  .checksum {
    font-family: monospace;
    /* margin-left: 2em;  /* indent */
  }
  #shortlog {
    font-size: large;
  }
  #shortlog td {
    vertical-align: top;
  }
  .author-cell {
    padding-top: 1em;
    padding-bottom: 1em;
    font-weight: bold;
    color: darkgreen;
  }
</style>

This is the latest version of Oils, a Unix shell that's our upgrade path from
[bash][]:

[bash]: \$xref

<div class="attention">

[Oils version $OILS_VERSION][release-index] - Source tarballs and documentation.

</div>

To build and run it, follow the instructions in [INSTALL.txt][].  The wiki has
tips on [How To Test OSH](\$wiki).

If you're new to the project, see [Why Create a New Shell?][why-oil] and posts
tagged #[FAQ](\$blog-tag).

[INSTALL.txt]: /release/$OILS_VERSION/doc/INSTALL.html
[github-bugs]: https://github.com/oils-for-unix/oils/issues
[why-oil]: ../../2021/01/why-a-new-shell.html
[release-index]: /release/$OILS_VERSION/

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

[changelog]: /release/$OILS_VERSION/changelog.html

<table id="shortlog">
EOF

  #contrib-commit-table
  devtools/release-version.sh git-shortlog-html release/$PREV_VERSION release/$OILS_VERSION

  cat <<EOF
</table>

## Documentation Updated

- [Known Differences](/release/$OILS_VERSION/doc/known-differences.html)
- [Interpreter State](/release/$OILS_VERSION/doc/interpreter-state.html) - still
	a draft.

### Wiki Pages

- [How Interactive Shells Work](https://github.com/oils-for-unix/oils/wiki/How-Interactive-Shells-Work)


## What's Next?

Here are some notable Open Issues

- [Provide APIs to allow users to write their own line editor / interactive
interface](\$issue:663)

## Appendix: Metrics for the $OILS_VERSION Release

Let's review release metrics, which help me keep track of the project.  The last review was in May, in [Metrics for the 0.29.0 Release](../05/metrics.html).

### Docs

We continue to improve the [Oils Reference](/release/0.35.0/doc/ref/).  In addition to adding new topics, I polished existing topics.

- [Doc Metrics for 0.29.0](//oils.pub/release/0.29.0/doc/metrics.txt) - **428** topics with first pass, **455** marked implemented, **496** unique
- [Doc Metrics for 0.35.0](//oils.pub/release/0.35.0/doc/metrics.txt) - **442** topics with first pass, **466** marked implemented, **510** unique

[NLnet]: https://nlnet.nl

### Spec Tests

[OSH][] made good progress, with **91** new passing spec tests.



- [OSH spec tests for 0.29.0](//oils.pub/release/0.29.0/test/spec.wwz/osh-py/index.html): **2517** tests, **2248** passing, **134** failing
- [OSH spec tests for 0.35.0](//oils.pub/release/0.35.0/test/spec.wwz/osh-py/index.html): **2608** tests, **2328** passing, **156** failing

But it also feels like there are too many failing tests.  

Let's look at the C++ translation:

[CPython]: \$xref:cpython

- [C++ spec tests for 0.29.0](//oils.pub/release/0.29.0/test/spec.wwz/osh-cpp/compare.html) - **2240** of **2248** passing - delta **8**
- [C++ spec tests for 0.35.0](//oils.pub/release/0.35.0/test/spec.wwz/osh-cpp/compare.html) - **2322** of **2328** passing - delta **6**

---

[YSH][] has **40** more tests passing:

- [YSH spec tests for 0.29.0](//oils.pub/release/0.29.0/test/spec.wwz/ysh-py/index.html): **1090** tests, **1022** passing, **68** failing
- [YSH spec tests for 0.35.0](//oils.pub/release/0.35.0/test/spec.wwz/ysh-py/index.html): **1133** tests, **1062** passing, **71** failing

They all pass in the C++ translation:

- [YSH C++ spec tests for 0.29.0](//oils.pub/release/0.29.0/test/spec.wwz/ysh-cpp/compare.html): **1020** of **1022** passing, delta **2**
- [YSH C++ spec tests for 0.35.0](//oils.pub/release/0.35.0/test/spec.wwz/ysh-cpp/compare.html): **1060** of **1062** passing, delta **2**

(The delta is again due to a \`Dict\` ordering issue in [Hay](\$xref:hay), which is harmless right now)

[YSH]: \$xref

### Benchmarks

No significant changes in parser speed:

- [Parser Performance for 0.29.0](//oils.pub/release/0.29.0/benchmarks.wwz/osh-parser/): **12.9** thousand irefs per line
- [Parser Performance for 0.35.0](//oils.pub/release/0.35.0/benchmarks.wwz/osh-parser/): **12.3**
  thousand irefs per line

Or memory usage:

- [benchmarks/gc for 0.29.0](//oils.pub/release/0.29.0/benchmarks.wwz/gc/): \`parse.configure-coreutils\` **1.65 M** objects comprising **41.0 MB**, max RSS **46.6 MB**
- [benchmarks/gc for 0.35.0](//oils.pub/release/0.35.0/benchmarks.wwz/gc/): \`parse.configure-coreutils\` **1.65 M** objects comprising **44.6 MB**, max RSS **50.8 MB**

#### Runtime

A compute-bound workload is the same speed:

- [benchmarks/gc-cachegrind for 0.29.0](//oils.pub/release/0.29.0/benchmarks.wwz/gc-cachegrind/) - \`fib\` takes **25.4** million irefs, mut+alloc+free+gc
- [benchmarks/gc-cachegrind for 0.35.0](//oils.pub/release/0.35.0/benchmarks.wwz/gc-cachegrind/) - \`fib\` takes **25.4** million irefs, mut+alloc+free+gc

This is the **infamous** autotools \`configure\` workload, which unfortunately has **noisy** measurements:

- [Runtime Performance for 0.29.0](//oils.pub/release/0.29.0/benchmarks.wwz/osh-runtime/) on 2 machines
  - **0.96x** and **1.05x** the speed of bash on \`configure.cpython\`
  - **1.04x** and **1.10x** the speed of bash on \`configure.util-linux\`
- [Runtime Performance for 0.35.0](//oils.pub/release/0.35.0/benchmarks.wwz/osh-runtime/) on 2 machines
  - **0.95x** and **0.87x** the speed of bash on \`configure.cpython\`
  - **1.04x** and **1.00x** the speed of bash on \`configure.util-linux\`

#### Code Size

Even though many new tests pass, our code is still short:

- [cloc for 0.29.0](//oils.pub/release/0.29.0/pub/metrics.wwz/line-counts/cloc-report.txt)
  - **25,185** significant lines in [OSH][], **6,380** in [YSH](\$xref), **1,691** in data languages
  - **6,112** lines of hand-written C++
- [cloc for 0.35.0](//oils.pub/release/0.35.0/pub/metrics.wwz/line-counts/cloc-report.txt)
  - **25,594** significant lines in [OSH][], **6,617** in [YSH](\$xref), **1,690** in data languages
  - **6,401** lines of hand-written C++

The generated C++ is proportional:

- [oils-cpp for 0.29.0](//oils.pub/release/0.29.0/pub/metrics.wwz/line-counts/oils-cpp.txt) - **128,449** physical lines
- [oils-cpp for 0.35.0](//oils.pub/release/0.35.0/pub/metrics.wwz/line-counts/oils-cpp.txt) - 193,303 - 62,484 = **130,819** physical lines (accounting another source file)

And compiled binary size is proportional:

- [ovm-build for 0.29.0](//oils.pub/release/0.29.0/benchmarks.wwz/ovm-build/):
  **2.40 MB** of native code (hoover, under GCC, on Debian 12)
- [ovm-build for 0.35.0](//oils.pub/release/0.35.0/benchmarks.wwz/ovm-build/):
  **2.42 MB** of native code (hoover, under GCC, on Debian 12)

&nbsp;

EOF
}

"$@"

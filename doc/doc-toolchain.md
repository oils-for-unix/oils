---
in_progress: yes
---

How We Build Oils Documentation
================================

1. Write Markdown by hand, with optional "front matter".
2. Render Markdown to HTML, and run the result through our own HTML filters.
3. Publish static HTML to <https://www.oilshell.org/>.

The code is in the [doctools/]($oils-src) directory, which uses the
[lazylex/]($oils-src)  library.

<div id="toc">
</div>

## Quick Start

To build and preview this doc, run:

    build/doc.sh split-and-render doc/doc-toolchain.md

Open the path in prints in your browser
(`_release/VERSION/doc/doc-toolchain.html`).

## Front Matter and Title

Most docs start with something like this:

    ---
    in_progress: yes
    default_highlighter: oils-sh
    ---

    My Title
    ========

    Hello

The "front matter" between `---` lines is metadata for rendering the doc.
Github's web UI understands and renders it.

## Plugins That Transform HTML

We have some HTML plugins that make writing **markdown** easier.
Note that [CommonMark][] tightens up the rules for embedding HTML in Markdown,
and that is very useful.

[CommonMark]: https://www.oilshell.org/blog/2018/02/14.html 

### Table of Contents

Insert this into the doc

    <div id="toc">
    </div>

and it will be expanded into a table of contents derived from `h2` and `h3`
tags.

### Link Shortcuts, e.g. `$xref`

Here's an example of how it works.  This Markdown:

    The [GNU bash shell]($xref:bash)

is translated to HTML by [CommonMark][]:

    The <a href="$xref:bash">GNU bash shell</a>

Our `$xref:` plugin expands it to:

    The <a href="/cross-ref.html#bash">GNU bash shell</a>

If the argument is omitted, then the **anchor text** is used.  So you can just write:

    [bash][]

and it will become:

    The <a href="/cross-ref.html#bash">bash</a>

List of plugins:

- `$xref:bash` expands to `/cross-ref.html#bash` (shown above)
- `$blog-tag:oil-release` expands to `/blog/tags.html#oil-release`
- `$oils-src`

See the raw and rendered versions of this doc for more:

- [doc-plugins.md][]
- [doc-plugins.html](doc-plugins.html)

[doc-plugins.md]: $oils-src:doc/doc-plugins.md

### Syntax Highlighting of Code Blocks

Use Markdown's fenced code blocks like this:

    ``` sh-prompt
    ysh$ var x = 'hello world'
    ysh$ echo $x
    hello world
    ```

Or you can set `default_highlighter` for blocks indented by 4 spaces.

Again see [doc-plugins.md][] for examples.

## The Help Toolchain Renders to HTML and ANSI

This is done with `doctools/`

## Code Location

- [build/doc.sh]($oils-src) drives the tools in [doctools/]($oils-src).
- Markdown files are in [doc/]($oils-src).



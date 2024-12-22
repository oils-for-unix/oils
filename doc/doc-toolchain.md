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

Markdown:

    The [GNU bash shell]($xref:bash)

After [CommonMark][]:

    The <a href="$xref:bash">GNU bash shell</a>

After our `$xref:` plugin:

    The <a href="/cross-ref.html#bash">GNU bash shell</a>

Example: The [GNU bash shell]($xref:bash)

---

If the argument is omitted, then the **anchor text** is used.  So you can just write:

    [bash][]

and it will become:

    The <a href="/cross-ref.html#bash">bash</a>

Example: [bash][]

[bash]: $xref

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

    ```oil-sh
    ysh$ var x = 'hello world'
    ysh$ echo $x
    hello world
    ```

Example:

```oil-sh
ysh$ var x = 'hello world'
ysh$ echo $x
hello world
```


Or you can set `default_highlighter` for blocks indented by 4 spaces.

Again see [doc-plugins.md][] for examples.

## Convenient Tables with `ul-table`

Our `ul-table` plugin allows you to write HTML **tables** as bulleted
**lists**.

Why?

- Because writing and maintaining `<tr>` and `<td>` and `</td>` and `</tr>` is
  tedious.
  - And putting markdown inside the `<td>` cells is verbose.
- Because Markdown can express bulleted lists, so your file remains **valid**
  Markdown.

That is, there is **no** new syntax.  The `ul-table` format is **not** a
Markdown language extension.

---

Here's a simple example.  Suppose you want to make this table:

<style>
table {
  margin: 0 auto;
}
thead {
  font-weight: bold;
}
td {
  padding: 5px;
}
</style>

<table>

- thead
  - Shell
  - Version
- tr
  - [bash]($xref)
  - 5.2
- tr
  - [OSH]($xref)
  - 0.25.0

</table>

Then you create a **two-level Markdown list** inside `<table>` tags, which
gives you `<table><ul> ... </ul></table>` when rendered:

    <table>

    - thead
      - Shell
      - Version
    - tr
      - [bash]($xref)
      - 5.2
    - tr
      - [OSH]($xref)
      - 0.25.0

    </table>

Then **our plugin** transforms the `<ul>` into a `<tr> <td>` structure.

---

Here's the stylesheet:

    <style>
    table {
      margin: 0 auto;
    }
    thead {
      font-weight: bold;
    }
    td {
      padding: 5px;
    }
    </style>

---

If you wanted to create this with pure Markdown, it would look **worse**:

    <table>
      <thead>
        <tr>
          <td>Shell</td>
          <td>Version</td>
        </tr>
      </thead>
      <tr>
        <td>

        [bash]($xref)

        </td>
        <td>5.2</td>
      </tr>
      <tr>
        <td>

        [OSH]($xref)

        </td>
        <td>0.25.0</td>
      </tr>

    </table>

---

By the way, if you omit the `<table>` tags, then the bulleted list looks like
this:

- thead
  - Shell
  - Version
- tr
  - [bash]($xref)
  - 5.2
- tr
  - [OSH]($xref)
  - 0.25.0

Remember, this is **not** an extension to Markdown **syntax**.

---

Here's a more complex example:

<table id="foo">

- thead
  - Shell
  - Version
  - Example Code
- tr
  - [bash][]
  - 5.2
  - ```
    echo sh=$bash
    ls /tmp | wc -l
    echo
    ```
- tr
  - [dash]($xref)
  - 1.5
  - <em>Inline HTML</em>
- tr
  - [mksh]($xref)
  - 4.0
  - <table>
      <tr>
        <td>HTML table</td>
        <td>inside</td>
      </tr>
      <tr>
        <td>this table</td>
        <td>no way to re-enter inline markdown though?</td>
      </tr>
    </table>

</table>

### Features

- Any markdown can be in a cell, which means any HTML can be in a cell
  - code blocks with bacticks
  - arbitrary HTML inside Markdown
  - TODO: nested lists
- TODO: Attributes for columns, rows, and cells
  - `<ul-col class=foo />`
     - Note: I ran into problems with `<colgroup>`
     - Example: Justify columns left and right
  - `<ul-row class=foo />`
  - `<ul-td colspan=2 />`
- Note: should have a custom rule of numbers to right, text to left?
  - I think `web/table/` has that rule

<!--

- CSS is written manually?  See `blog/2024/09/project-overview.html`, etc.
  - Or we could have a default

-->

## Code Location

- [build/doc.sh]($oils-src) drives the tools in [doctools/]($oils-src).
- Markdown files are in [doc/]($oils-src).



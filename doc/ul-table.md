ul-table: Markdown Tables Without New Syntax
================================

Our `ul-table` plugin allows you to write HTML **tables** as bulleted
**lists**.

Why?

- Because writing and maintaining `<tr>` and `<td>` and `</td>` and `</tr>` is
  tedious.
- Because Markdown can express bulleted lists, so your file remains **valid**
  Markdown.
  - Your documentation still be readable when viewed with sourcehut or Github.

That is, this way of writing tables involves **no** new syntax.  It's not a
Markdown language extension.

<div id="toc">
</div>

## Simple Example

Suppose you want to make this table:

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

With `ul-table`, you create a **two-level Markdown list** inside `<table>`
tags:

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

Making an HTML table takes two steps:

1. The Markdown translator produces a
   `<table> <ul> <li> ... </li> </ul> </table>` structure.
1. **Our** `ul-table` plugin transforms that into a `<tr> <td> </td> </tr>`
   structure.

(This format is inspired by [tables in
reStructuredText](https://sublime-and-sphinx-guide.readthedocs.io/en/latest/tables.html).

### Pure Markdown Requires Tedious HTML

The bulleted lists are easier to **read and write**!  Here's the equivalent in
CommonMark:

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

It uses the rule where you can embed HTML inside markdown, and then markdown
inside HTML.

With `ul-table`, we **remove** this kind of mutual nesting (at least, one level
of it.)

### Stylesheet

To make the table look nice, I use `<style>` tags inside Markdown:

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

### The Untranslated Markdown

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

This is how your tables will appear on sourcehut or Github &mdash; the contents
are still readable.  Remember, `ul-table` is **not** an extension to Markdown
**syntax**.

## More Complex Example

[bash]: $xref

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
- tr
  - [zsh]($xref)
  - 3.6
  - Unordered List
    - one
    - two
- tr
  - [yash]($xref)
  - 1.0
  - Ordered List
    1. one
    1. two
- tr
  - [ksh]($xref)
  - This is
    paragraph one.

    This is
    paragraph two
  - Another cell with ...

    ... multiple paragraphs.

</table>

## Features

- Any markdown can be in a cell
  - paragraphs, code blocks with backticks, nested lists
  - Markdown supports arbitrary HTML, so arbitrary HTML can be in a cell
    - no new rules to learn!
- TODO: Attributes for columns, rows, and cells
  - `<ul-col class=foo />`
     - Note: I ran into problems with `<colgroup>`
     - Example: Justify columns left and right
  - `<ul-row class=foo />`
  - `<ul-td colspan=2 />`

Note: should have a custom rule of aligning numbers to right, and text to left?
I think `web/table/` has that rule.

<!--

- CSS is written manually?  See `blog/2024/09/project-overview.html`, etc.
  - Or we could have a default

-->


## Related Docs

- [How We Build Oils Documentation](doc-toolchain.html)
- [Examples of HTML Plugins](doc-plugins.html)

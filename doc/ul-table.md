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

With `ul-table`, you type a **two-level Markdown list**, inside `<table>` tags:

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

(This format looks similar to [tables in
reStructuredText](https://sublime-and-sphinx-guide.readthedocs.io/en/latest/tables.html)).

The conversion takes two steps:

1. Any Markdown translator will produce a
   `<table> <ul> <li> ... </li> </ul> </table>` structure.
1. **Our** `ul-table` plugin transforms that into a
   `<table> <tr> <td> </td> </tr> </table>` structure, which is a normal HTML
   table.

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
syntax.

## More Complex Example

View the source code of this table: [doc/ul-table.md]($oils-src)

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

## Real Examples in Oils

TODO

- docs
  - convert proc-func table
  - interior/exterior?
- blog
  - What Oils Looks Like in 2024
  - Line Counts
  - Narrow waist?  diagrams

## `ul-table` Features

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


## Appendix

### Related Docs

- [How We Build Oils Documentation](doc-toolchain.html)
- [Examples of HTML Plugins](doc-plugins.html)

### Our Style is Nicer Than Github's

Github-flavored Markdown has an non-standard extension for tables:

- [Github: Organizing Information With Tables](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables)

This style is hard to read and write, especially with large tables:

```
| Command | Description |
| --- | --- |
| git status | List all new or modified files |
| git diff | Show file differences that haven't been staged |
```

Our style is less noisy and more easily editable:

```
- thead
  - Command
  - Description
- tr
  - git status
  - List all new or modified files
- tr
  - git diff
  - Show file differences that haven't been staged
```

### CommonMark

- 2014 discussion: [Tables in pure Markdown](https://talk.commonmark.org/t/tables-in-pure-markdown/81)
- 2022 discussion: [Obvious Markdown syntax for Tables](https://talk.commonmark.org/t/obvious-markdown-syntax-for-tables/4143/9)


### Implemention

- [doctools/ul_table.py]($oils-src) - less than 400 lines
- [lazylex/html.py]($oils-src) - about 400 lines

TODO:

- Make it run under Python 3, including unit tests
- De-couple it from cmark.so
  - Use Unix pipes, with a demo in `doctools/ul-table.sh`

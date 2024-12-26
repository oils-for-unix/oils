ul-table: Markdown Tables Without New Syntax
================================

`ul-table` is an HTML processor that lets you write **tables** as bulleted
**lists**, in Markdown:

<!-- TODO: Add hyperlinks here, or maybe add markdown-->

```
<table>

- thead
  - Shell
  - Version
- tr
  - bash
  - 5.2
- tr
  - OSH
  - 0.25.0

</table>
```

<table>

- thead
  - Shell
  - Version
- tr
  - bash
  - 5.2
- tr
  - OSH
  - 0.25.0

</table>

I designed this format because it's tedious to read, write, and edit `<tr>` and
`<td>` and `</td>` and `</tr>`.  Aligning columns is also tedious in HTML.

`ul-table` does **not** involve new Markdown syntax, only a new interpretation.

This means your docs are still readable without it, e.g. on sourcehut or
Github.  It degrades gracefully.

---

Other design goals:

- It should scale to large, complex tables.
- Expose the **full** power of HTML, unlike other solutions.

<!--

- Solve the "column alignment problem" concisely.
  - HTML punts on this, as explained below.
-->

<div id="toc">
</div>

## Simple Example

Let's add hyperlinks to our example, to make it more realistic.

<style>
table {
  margin: 0 auto;
}
td {
  padding: 0.2em;
}
</style>

<table>

- thead
  - Shell
  - Version
- tr
  - [bash](https://www.gnu.org/software/bash/)
  - 5.2
- tr
  - [OSH](https://www.oilshell.org/)
  - 0.25.0

</table>

### `ul-table` Syntax

You can make this table with a **two-level Markdown list**, with Markdown
hyperlink syntax:

    <table>  <!-- don't forget this tag -->

    - thead
      - Shell
      - Version
    - tr
      - [bash](https://www.gnu.org/software/bash/)
      - 5.2
    - tr
      - [OSH](https://www.oilshell.org/)
      - 0.25.0

    </table>

(This format looks similar to [tables in
reStructuredText](https://sublime-and-sphinx-guide.readthedocs.io/en/latest/tables.html)).

It takes two steps to convert:

1. Any Markdown translator will produce a
   `<table> <ul> <li> ... </li> </ul> </table>` structure.
1. **Our** `ul-table` plugin transforms that into a
   `<table> <tr> <td> </td> </tr> </table>` structure, which is a normal HTML
   table.

### Comparison: Markdown Uses Tedious Inline HTML

Here's the equivalent in CommonMark:

    <table>
      <thead>
        <tr>
          <td>Shell</td>
          <td>Version</td>
        </tr>
      </thead>
      <tr>
        <td>

    <!-- be careful not to indent this 4 spaces! -->
    [bash](https://www.gnu.org/software/bash/)

        </td>
        <td>5.2</td>
      </tr>
      <tr>
        <td>

    [OSH](https://www.oilshell.org/)

        </td>
        <td>0.25.0</td>
      </tr>

    </table>

It uses the rule where you can embed Markdown inside HTML inside Markdown.
With `ul-table`, you **don't** need this mutual nesting.

The text you have to write is also a lot shorter!

---

Trivia: with CommonMark, you also get an extra `<p>` element:

    <td>
      <p>OSH</p>
    </td>

`ul-table` can produce simpler HTML:

    <td>
      OSH
    </td>

### Stylesheet

To make the table look nice, I add a `<style>` tag, inside Markdown:

    <style>
    table {
      margin: 0 auto;
    }
    td {
      padding: 0.2em;
    }
    </style>

### The Untranslated HTML

If you omit the `<table>` tags, then the rendered HTML looks like this:

- thead
  - Shell
  - Version
- tr
  - [bash]($xref)
  - 5.2
- tr
  - [OSH]($xref)
  - 0.25.0

This is how your tables will appear on sourcehut or Github, which don't (yet)
have `ul-table` support.  Remember, `ul-table` is **not** an extension to
Markdown syntax.

## Adding HTML Attributes

HTML attributes like `<tr class=foo>` and `<td id=bar>` let you format and
style your table.

You can add attributes to cells, columns, and rows.

### Cells

Add cell attributes with a `cell-attrs` tag **before** the cell contents:

    - thead
      - Name
      - Age
    - tr
      - Alice
      - <cell-attrs class=num /> 42

It's important that `cell-attrs` is a **self-closing** tag:

    <cell-attrs />  # Yes
    <cell-attrs>    # No: this is an opening tag

How does this work?  `ul-table` takes the attributes from `<cell-attrs />`, and
puts it on the generated `<td>`.

### Columns

Add attributes to **every cell in a column** by the same way, except in the
`thead` section:

    - thead
      - Name
      - <cell-attrs class=num /> Age
    - tr
      - Alice
      - 42     # this cell gets class=num
    - tr
      - Bob
      - 25     # this cells gets class=num

This is particularly useful for aligning numbers to the right:

    <style>
    .num {
      text-align: right;
    }
    </style>

If the same attribute appears in the `thead` and and a `tr` section, the values
are **concatenated**, with a space.  Example:

    <td class="from-thead from-tr">

### Rows

Add row attributes like this:

    - thead
      - Name
      - Age
    - tr
      - Alice
      - 42
    - tr <row-attrs class="special-row />
      - Bob
      - 25

## Example: Markdown and HTML Inside Cells

Here's an example that uses more features.  Source code of this table:
[doc/ul-table.md]($oils-src).

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

## Markdown Quirks to Be Aware Of

Here are some quirks I ran into when creating ul-tables.

(1) CommonMark doesn't allow empty list items:

    - thead
      -
      - above is not rendered as a list item

You can work around this by using a comment, or invisible character:

    - tr
      - <!-- empty -->
      - above is OK
    - tr
      - &nbsp;
      - also OK

- [Related CommonMark thread](https://talk.commonmark.org/t/clarify-following-empty-list-items-in-0-31-2/4599)

As similar issue is that line breaks affect backtick expansion to `<code>`:

    - tr
      - <cell-attrs /> <!-- we need something on this line -->
        ... More `proc` features ...

I think this is also because `<cell-attrs />` doesn't "count" as text, so the
list item is considered empty.

(2) Likewise, a cell with a literal hyphen may need a comment or space in front of it:

    - tr
      - <!-- hyphen --> -
      - &nbsp; -

## Comparisons

### CommonMark Doesn't Have Tables

Related discussions:

- 2014: [Tables in pure Markdown](https://talk.commonmark.org/t/tables-in-pure-markdown/81)
- 2022: [Obvious Markdown syntax for Tables](https://talk.commonmark.org/t/obvious-markdown-syntax-for-tables/4143/9)

### Github Tables are Awkward

Github-flavored Markdown has an non-standard extension for tables:

- [Github: Organizing Information With Tables](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables)

This style is hard to read and write, especially with large tables:

```
| Command | Description |
| --- | --- |
| git status | List all new or modified files |
| git diff | Show file differences that haven't been staged |
```

Our style is less noisy, and more easily editable:

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

- Related wiki page: [Markdown Tables]($wiki)


## Conclusion

`ul-table` is a nice way of writing and maintaining HTML tables.  The appendix
has links and details.

### Related Docs

- [How We Build Oils Documentation](doc-toolchain.html)
- [Examples of HTML Plugins](doc-plugins.html)

## Appendix: Implemention

- [doctools/ul_table.py]($oils-src) - about 500 lines
- [lazylex/html.py]($oils-src) - about 500 lines

TODO:

- Move unit tests to spec tests - `doctools/ul-table-test.ysh`
  - can run under Python 2 vs. Python 3
  - can run with cmark vs. `markdown.pl`
    - De-couple it from cmark.so
- Publish the code separately?
  - `lazylex/html.py` can got in `doctools/`
  - or maybe it's ready to go in `data_lang/htm8.py`, if we can fix the lexer
- Could revive pyannotate automation to help with the typing

### Algorithm Notes

- lazy lexing
- recursive descent parser
  - TODO: show grammar

TODO:

- I would like someone to produce a **DOM** implementation!
  - Our implementation is meant to avoid the "big load anti-pattern"
    (allocating too much), so it's a necessarily more verbose.  A DOM
    implementation should be much less than 1000 lines.


## Appendix: Real Examples

- [Guide to Procs and Funcs]($oils-doc:proc-func.html) has a big `ul-table`.
  - Source: [doc/proc-func.md]($oils-src)

I converted the tables in these September posts to `ul-table`:

- [What Oils Looks Like in 2024](https://www.oilshell.org/blog/2024/09/project-overview.html)
- [After 8 Years, Oils Is Still Small and Flexible](https://www.oilshell.org/blog/2024/09/line-counts.html)
- [Garbage Collection Makes YSH Different](https://www.oilshell.org/blog/2024/09/gc.html)
- [A Retrospective on the Oils Project](https://www.oilshell.org/blog/2024/09/retrospective.html)

The markup was much shorter and simpler after conversion!

TODO:

- Tables to Make
  - Interior/Exterior
  - Narrow Waist

- Wiki pages could use conversion
  - [Alternative Shells]($wiki)
  - [Alternative Regex Syntax]($wiki)
  - [Survey of Config Languages]($wiki)
  - [Polyglot Language Understanding]($wiki)
  - [The Biggest Shell Programs in the World]($wiki)


## HTML Quirks

- `<th>` is like `<td>`, but it belongs in `<thead><tr>`.  Browsers make it
  bold and centered.
- You can't put `class=` on `<colgroup>` and `<col>` and align columns left and
  right.
  - You have to put `class=` on *every* `<td>` cell instead.
  - `ul-table` solves this with "inherited" `<cell-attrs />` in the `thead`
    section.

<!--

### FAQ

(1) Why do row with attributes look like `tr <row-attrs />`?   The first `tr`
doesn't seem neecssary.

This is because of the CommonMark quirk above: a list item without **text** is
treated as **empty**.  So we require the extra `tr` text.

It's also consistent with plain rows, without attributes.

-->

## Feature Ideas

We could help users edit well-formed tables with enforced column names:

    - thead
      - <cell-attrs ult-name=name /> Name
      - <cell-attrs ult-name=age /> Age
    - tr 
      - <cell-attrs ult-name=name /> Hi
      - <cell-attrs ult-name=age /> 5

This is a bit verbose, but may be worth it for large tables.

Less verbose syntax idea:

    - thead
      - <ult col=NAME /> <cell-attrs class=foo /> Name
      - <ult col=AGE /> Age
    - tr 
      - <ult col=NAME /> Hi
      - <ult col=AGE /> 5

Even less verbose:

    - thead
      - {NAME} Name
      - {AGE} Age
    - tr 
      - {NAME} Hi
      - {AGE} 5

The obvious problem is that we might want the literal text `{NAME}` in the
header.  It's unlikely, but possible.


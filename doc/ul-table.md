ul-table: Markdown Tables Without New Syntax
================================

`ul-table` is an HTML processor that lets you write **tables** as bulleted
**lists**, in Markdown.

It's a short program I wrote because I got tired of reading and writing `<tr>`
and `<td>` and `</td>` and `</tr>`.  And I got tired of aligning numbers by
writing `<td class="num">` for every cell.

<div id="toc">
</div>

## Simple Example

Let's see how it works.  How do you make this table?

<style>
table {
  margin: 0 auto;
}
td {
  padding-left: 1em;
  padding-right: 1em;
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
  - [OSH](https://oils.pub/)
  - 0.25.0

</table>

With `ul-table`, you create a **two-level** Markdown list, inside `<table>`
tags:

<!-- TODO: Add pygments highlighting -->

```
<table>

- thead
  - Shell
  - Version
- tr
  - [bash](https://www.gnu.org/software/bash/)
  - 5.2
- tr
  - [OSH](https://oils.pub/)
  - 0.25.0

</table>
```

The header and data rows are at the top level, and the cells are indented under
them.

---

The conversion takes **2 steps**: it's Markdown &rarr; HTML &rarr; HTML.

First, any Markdown processor will produce this list structure, with `<ul>` and
`<li>`:

- thead
  - Shell
  - Version
- tr
  - [bash](https://www.gnu.org/software/bash/)
  - 5.2
- tr
  - [OSH](https://oils.pub/)
  - 0.25.0

Second, **our** `ul-table` plugin parses and transforms that into a table, with
`<tr>` and `<td>`:

<table>

- thead
  - Shell
  - Version
- tr
  - [bash](https://www.gnu.org/software/bash/)
  - 5.2
- tr
  - [OSH](https://oils.pub/)
  - 0.25.0

</table>

So `ul-table` is an HTML processor, **not** a Markdown processor.  But it's
meant to be used with Markdown.

## Design 

### Goals

<!--
This means your docs are still readable without it, e.g. on sourcehut or
Github.  It degrades gracefully.
-->

- Don't invent any new syntax.
  - It reuses your knowledge of Markdown &mdash; e.g. hyperlinks.
  - It reuses your knowledge of HTML &mdash; e.g. attributes on tags.
- Large, complex tables should be maintainable.
- The user should have the **full** power of HTML.  We don't hide it under
  another language, like MediaWiki does.
- Degrade gracefully.  Because it's just Markdown, you **won't break** docs by
  adding it.
  - The intermediate list form is what sourcehut or Github will show.

### Comparison

Compared to other table markup formats, `ul-table` is shorter, less noisy, and
easier to edit:

- [ul-table Comparison: Github, Wikipedia, reStructuredText, AsciiDoc](ul-table-compare.html)

## Details

### ul-table "Grammar"

Recall that a `ul-table` is a **two-level Markdown list**, between `<table>`
tags.  The top level list contains either:

<table>

- tr
  - `thead`
  - zero or one, at the beginning
- tr
  - `tr` 
  - zero or more, after `thead`

</table>

The second level contains the contents of cells, but you **don't** write `td`
or `<td>`.

### Stylesheet

To make the table look nice, I add a `<style>` tag, inside Markdown:

    <style>
    table {
      margin: 0 auto;
    }
    td {
      padding-left: 1em;
      padding-right: 1em;
    }
    </style>

## Adding HTML Attributes

HTML attributes like `<tr class=foo>` and `<td id=bar>` let you format and
style your table.

You can add attributes to cells, columns, and rows.

### Cells

<style>
.hi { background-color: thistle }
</style>

<table>

- thead
  - Name
  - Age
- tr
  - Alice
  - 42 <cell-attrs class=hi />
- tr
  - Bob
  - 9

</table>

Add cell attributes with a `cell-attrs` tag after the cell contents:

```
- thead
  - Name
  - Age
- tr
  - Alice
  - 42 <cell-attrs class=hi />
- tr
  - Bob
  - 9
```

You must use a **self-closing** tag:

    <cell-attrs />  # Yes
    <cell-attrs>    # No: this is an opening tag

Notice that `ul-table` takes the attributes from the `<cell-attrs />` tag, and
puts it on the generated `<td>` tag.

### Columns

<style>
.num {
  text-align: right;
}
</style>

<table>

- thead
  - Name
  - Age <cell-attrs class=num /> 
- tr
  - Alice
  - 42
- tr
  - Bob
  - 9

</table>

To add attributes to **every cell in a column**, put `<cell-attrs />` in the
`thead` section:

<style>
.num {
  background-color: bisque;
  align: right;
}
</style>

```
- thead
  - Name
  - Age <cell-attrs class=num /> 
- tr
  - Alice
  - 42     <!-- this cell gets class=num -->
- tr
  - Bob
  - 9      <!-- this cells gets class=num -->
```

Then every `<td>` in the column will "inherit" those attributes.  This is
useful for aligning numbers to the right:

    <style>
    .num {
      align: right;
    }
    </style>

If the same attribute appears in a column in both `thead` and `tr`, the values
are **concatenated**, with a space.  Example:

    <td class="from-thead from-tr">

### Rows

<style>
.special-row {
  background-color: powderblue;
}
</style>

<table>

- thead
  - Name
  - Age
- tr
  - Alice
  - 42
- tr <row-attrs class="special-row "/>
  - Bob
  - 9

</table>

To add row attributes, put `<row-attrs />` after the `- tr`:

    - thead
      - Name
      - Age
    - tr
      - Alice
      - 42
    - tr <row-attrs class="special-row" />
      - Bob
      - 9

## More Complex Example

This example uses more features, like Markdown and HTML inside cells.  You may
want to view the source text for this table: [doc/ul-table.md]($oils-src).

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

&nbsp;

Another table:

<style>
.osh-code { color: darkred }
.ysh-code { color: darkblue }
</style>


<table>

- thead
  - OSH
  - YSH
- tr
  - ```
    my-copy() {
      cp --verbose "$@"
    }
    ```
    <cell-attrs class=osh-code /> 
  - ```
    proc my-copy {
      cp --verbose @ARGV
    }
    ```
    <cell-attrs class=ysh-code />
- tr
  - x
  - y

</table>


## Markdown Quirks

Here are some quirks I ran into when using `ul-table`.

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

(2) Similarly, a cell with a literal hyphen may need a comment or space in
front of it:

    - tr
      - <!-- hyphen --> -
      - &nbsp; -

## Conclusion

`ul-table` is a nice way of writing and maintaining HTML tables.  The appendix
has links and details.

### Related Docs

- [ul-table Comparison: Github, Wikipedia, reStructuredText, AsciiDoc](ul-table-compare.html)
- [How We Build Oils Documentation](doc-toolchain.html)
- [Examples of HTML Plugins](doc-plugins.html)

## Appendix: Implemention

- [doctools/ul_table.py]($oils-src) - about 500 lines
- [lazylex/html.py]($oils-src) - about 500 lines

### Notes on the Algorithm

- lazy lexing
- recursive descent parser
  - TODO: show grammar

TODO: I would like someone to produce a **DOM**-based implementation!

Our implementation is pretty low-level.  It's meant to avoid the "big load
anti-pattern" (allocating too much), so it's a necessarily more verbose.

A DOM-based implementation should be much less than 1000 lines.

## Appendix: Real Examples

- Docs
  - [Guide to Procs and Funcs]($oils-doc:proc-func.html) has a big `ul-table`.
    Source: [doc/proc-func.md]($oils-src)
- Site
  - [oils.pub Home Page](/)
  - [Blog Index](/blog/)

I converted the tables in these September posts to `ul-table`:

- [What Oils Looks Like in 2024](https://www.oilshell.org/blog/2024/09/project-overview.html)
- [After 8 Years, Oils Is Still Small and Flexible](https://www.oilshell.org/blog/2024/09/line-counts.html)
- [Garbage Collection Makes YSH Different](https://www.oilshell.org/blog/2024/09/gc.html)
- [A Retrospective on the Oils Project](https://www.oilshell.org/blog/2024/09/retrospective.html)
- [Oils 0.22.0 Announcement](https://www.oilshell.org/blog/2024/06/release-0.22.0.html#data-languages) - table of multi-line string litearls

The markup was much shorter and simpler after conversion!

TODO:

- More tables to Make
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
- `<colgroup>` and `<col>` often do do what I want.
  - As mentioned above, you can't put `class=` columns and align them to the
    right or left.  You have to put `class=` on *every* `<td>` cell instead.

<!--

### FAQ

(1) Why do row with attributes look like `tr <row-attrs />`?   The first `tr`
doesn't seem neecssary.

This is because of the CommonMark quirk above: a list item without **text** is
treated as **empty**.  So we require the extra `tr` text.

It's also consistent with plain rows, without attributes.

-->

## Ideas for Features

- Support `tfoot`?
- Emit `tbody`?

---

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


<!--

TODO: We should detect cell-attrs before the closing `</li>`, or in any
position?

<table>

- thead
  - OSH
  - YSH
- tr
  - ```
    my-copy() {
      cp --verbose "$@"
    }
    ```
    <cell-attrs class=osh-code />
  - ```
    proc my-copy {
      cp --verbose @ARGV
    }
    ```
    <cell-attrs class=ysh-code />

</table>

-->


<!--
TODO:

- change back to oilshell.org/ for publishing
- Compare to wikipedia
  - https://en.wikipedia.org/wiki/Help:Table
  - table caption  - this is just <caption>
  - rowspan
-->

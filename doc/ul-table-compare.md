---
in_progress: yes
---

ul-table Comparison
====================

TODO: This may go on the blog.

Main doc: [ul-table: Markdown Tables Without New Syntax](ul-table.html)

<div id="toc">
</div>

## Markdown-Based

### ul-table

### Plain Markdown

- You can't write inline HTML

### CommonMark

Tedious Inline HTML!

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

    [OSH](https://oils.pub/)

        </td>
        <td>0.25.0</td>
      </tr>

    </table>

It uses the rule where you can embed Markdown inside HTML inside Markdown.
With `ul-table`, you **don't** need this mutual nesting.

The `ul-table` text is also shorter!

---

Trivia: with CommonMark, you get an extra `<p>` element:

    <td>
      <p>OSH</p>
    </td>

`ul-table` can produce simpler HTML:

    <td>
      OSH
    </td>

- Inline HTML

CommonMark Doesn't Have Tables.  Related discussions:

- 2014: [Tables in pure Markdown](https://talk.commonmark.org/t/tables-in-pure-markdown/81)
- 2022: [Obvious Markdown syntax for Tables](https://talk.commonmark.org/t/obvious-markdown-syntax-for-tables/4143/9)


### Github-Flavored Markdown

Github Tables are Awkward.

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
<table>

- thead
  - Command
  - Description
- tr
  - git status
  - List all new or modified files
- tr
  - git diff
  - Show file differences that haven't been staged

</table>
```

- Related wiki page: [Markdown Tables]($wiki)



## Non-Markdown

### reStructuredText

ul-table looks similar to [tables in
reStructuredText](https://sublime-and-sphinx-guide.readthedocs.io/en/latest/tables.html).

### AsciiDoc

TODO

### MediaWiki (Wikipedia)

Here is a **long** page describing how to make tables on Wikipedia:

- <https://en.wikipedia.org/wiki/Help:Table>

I created the equivalent of the opening example:

```
{| class="wikitable"
! Shell !! Version
|-
| [https://www.gnu.org/software/bash/ Bash] || 5.2
|-
| [https://www.oilshell.org/ OSH] || 0.25.0
|}
```

In general, it has more "ASCII art", and invents a lot of new syntax.

I prefer `ul-table` because it reuses Markdown and HTML syntax.

---
in_progress: yes
default_highlighter: oils-sh
body_css_class: width50
---

Tables, Object, and Documents - Notation, Query, Creation, Schema
=============================

<style>
  thead {
    background-color: #eee;
    font-weight: bold;
    text-align: left;
  }
  table {
    font-family: sans-serif;
    border-collapse: collapse;
  }

  tr {
    border-bottom: solid 1px;
    border-color: #ddd;
  }

  td {
    padding: 8px;  /* override default of 5px */
  }
</style>

This is part of **maximal** YSH!

<div id="toc">
</div> 

## Philosophy

- Oils is Exterior-First
- Tables, Objects, Documents - CSV, JSON, HTML
  - Oils cleanup: TSV8, JSON8, HTM8

## Tables


<table>

- thead
  - Data Type
  - Notation
  - Query
  - Creation
  - Schema
- tr
  - Table
  - TSV, CSV
  - csvkit, xsv, awk-ish, etc. <br/>
    SQL, Data Frames
  - ?
  - ?
- tr
  - Object
  - JSON
  - jq <br/>
    JSONPath: MySQL/Postgres/sqlite support it?
  - jq
  - JSON Schema
- tr
  - Document
  - HTML5
  - DOM API like getElementById() <br/>
    CSS selectors <br/>
  - JSX Templates
  - ?
- tr
  - Document
  - XML
  - XPath?  XQuery?
  - XSLT?
  - three:
    - DTD (document type definition, 1986)
    - RelaxNG (2001)
    - XML Schema aka XSD (2001)

<!-- TODO: ul-table should allow caption at the top -->
<caption>Existing</caption>

</table>

&nbsp;

<table>

- thead
  - Data Type
  - Notation
  - Query
  - Creation
  - Schema
  - In-Memory
- tr
  - Table
  - TSV8 (is valid TSV)
  - dplyr-like Data Frames <br/>
    Maybe some SQL-pipe subset thing?
  - `table { }`
  - ?
  - By column: dict of "arrays" <br/>
    By row: list of dicts <br/>
- tr
  - Object
  - JSON8 (superset)
  - JSONPath? <br/>
    jq as a reshaping language
  - Hay?  `Package { }`
  - JSON Schema?
  - List and Dict
- tr
  - Document
  - HTM8 (subset)
  - CSS selectors
  - Markaby Style `div { }` <br/>
    "sed" style
  - ?
  - DocFrag - a span within a doc<br/>
    DocTree - an Obj representation<br/>
    ?

<caption>Oils</caption>

</table>

## Note: SQL Databases Support all three models!

- sqlite, MySQL, and PostGres obviously have tables
- They all have JSON and JSONPath support!
  - JSONPath syntax might differ a bit?
- XML support
  - Postgres: XML type, XPath, more
  - MySQL: XML extraction functions only
  - sqlite: none

## Design Issues

### Streaming

- jq has a line-based streaming model, by taking advantage of the fact that
  all JSON can be encoded without literal newlines
  - HTML/XML don't have this property
- Solution: Netstring based streaming?
  - can do it for both JSON8 and HTM8 ?

### Mutual Nesting

- JSON must be UTF-8, so JSON strings can contain JSON
  - ditto for JSON8, and J8 strings
- TSV cells can't contain tabs or newlines
  - so they can't contain TSV
  - if you remove all the newlines, they can contain JSON
- TSV8 cells use J8 strings, so they can contain JSON, TSV
- HTM8
  - you can escape everything, so you can put another HTM8 doc inside
  - and you can put JSON/JSON8 or TSV/TSV8
  - although are there whitespace rules?
  - all nodes can be liek `<pre>` nodes, preserving whitespace, until
    - you apply another function to it

### HTML5 whitespace rules

- inside text context:
  - multiple whitespace chars collapsed into a single one
  - newlines converted to spaces
  - leading and trailing space is preserved
- `<pre> <code> <textarea>`
  - whitespace is preserved exactly as written
    - I guess HTM8 could use another function for this?
- quoted attributes
  - whitespace is untouched

## Related

- [stream-table-process.html](stream-table-process.html)
- [ysh-doc-processing.html](ysh-doc-processing.html)

## Notes

### RelaxNG, XSD, DTD

I didn't know there were these 3 schema types!

- DTD is older, associated with SGML created in 1986
- XML Schema and Relax NG created in 2001
  - XML Schema use XML syntax, which is bad!


### Algorithms?

- I looked at `jq`
- how do you do CSS selectors?
- how do you do JSONPath?

- XML Path
  - holistic twig joins - bounded memory
  - Hollandar Marx XPath Streaming


### Naming

- HTM8 doesn't use J8 strings
  - but TSV8 does

- Technically we could add j8 strings with
  - j''
  - and even templated strings with $"" ?
- hm
  - well then we would need $[ j'' ] and so forth

Is

- `<span x=j'foo'>` identical to `<span x="j'foo'">` in HTML5 ?
  - it seems do
  - ditto for `$""`
- then we could disallow those pattern in double quotes?
  - they would have to be quoted like &sq; or something

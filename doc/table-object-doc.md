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
  - HTML5, XML
  - DOM API like getElementById() <br/>
    CSS selectors <br/>
    XPath?
  - JSX Templates
  - XML Schema?

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

## Related

- [stream-table-process.html](stream-table-process.html)
- [ysh-doc-processing.html](ysh-doc-processing.html)

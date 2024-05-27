---
in_progress: yes
css_files: ../../web/base.css ../../web/ref-index.css ../../web/toc.css
preserve_anchor_case: yes
---

Data Notation Table of Contents
===

Shell programs can be built on well-defined data formats.

This page is part of the [Oils Reference](index.html).  (Siblings: [OSH
contents](toc-osh.html), [YSH contents](toc-ysh.html))

<!--
<div id="toc">
</div>
-->

<div class="custom-toc">

[front-end](#front-end) &nbsp; [j8-notation](#j8-notation) &nbsp;
[packle](#packle) &nbsp; [errors](#errors) &nbsp;

</div>

<h2 id="front-end">
  Front End (<a class="group-link" href="chap-front-end.html">front-end</a>)
</h2>

```chapter-links-front-end
  [Lexing]        ascii-whitespace [ \t\r\n]
                  ascii-control-chars
```

<h2 id="j8-notation">
  J8 Notation
  (<a class="group-link" href="chap-j8.html">j8</a>)
</h2>

```chapter-links-j8
  [J8 Strings]   json-string    "hi"
                 json-escape    \" \\ \u1234
                 surrogate-pair \ud83e\udd26
                 j8-escape      \' \u{1f926} \yff
                 u-prefix       u'hi'
                 b-prefix       b'hi'
                 no-prefix      'hi'
  [J8 Lines]     unquoted-line
  [JSON8]        json8-num      json8-str
                 json8-list     json-dict
                 json8-comment
  [TSV8]         column-attrs   column-types
```

All J8 notation is UTF-8.

<!--
<h2 id="packle">
  Packle
  (<a class="group-link" href="chap-packle.html">packle</a>)
</h2>

```chapter-links-packle
X [Atoms]    Null   Bool   Int   Float   Bytes   Unicode
X [Compound] List   Dict
```
-->

<h2 id="errors">
  Errors
  (<a class="group-link" href="chap-errors.html">errors</a>)
</h2>

```chapter-links-errors
  [UTF8]      err-utf8-encode       err-utf8-decode
  [J8 String] err-j8-str-encode     err-j8-str-decode
  [J8 Lines]  err-j8-lines-encode   err-j8-lines-decode
  [JSON]      err-json-encode       err-json-decode
  [JSON8]     err-json8-encode      err-json8-decode
X [Packle]    err-packle-encode     err-packle-decode
```

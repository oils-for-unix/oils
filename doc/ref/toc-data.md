---
in_progress: yes
css_files: ../../web/base.css ../../web/ref-index.css ../../web/toc.css
preserve_anchor_case: yes
---

Data Notation Table of Contents
===

These are links to topics in the [Oils Reference](index.html).

Siblings: [OSH Topics](toc-osh.html), [YSH Topics](toc-ysh.html)

<div id="toc">
</div>

<h2 id="j8-notation">
  J8 Notation
  (<a class="group-link" href="chap-j8.html">j8</a>)
</h2>

```chapter-links-j8
  [J8 Strings]   json-string "hi"   json-escape \" \\ \u1234
                 surrogate-pair \ud83e\udd26
                 u-prefix u'hi'   b-prefix b'hi'
                 j8-escape \u{1f926} \yff
  [JSON8]        Null   Bool   Number   
                 Json8String
                 List   Dict
  [TSV8]         column-attrs   column-types
```

All J8 notation is UTF-8.

<h2 id="packle">
  Packle
  (<a class="group-link" href="chap-packle.html">packle</a>)
</h2>

```chapter-links-packle
  [Atoms]    Null   Bool   Int   Float   Bytes   Unicode
  [Compound] List   Dict
```

<h2 id="errors">
  Errors
  (<a class="group-link" href="chap-errors.html">errors</a>)
</h2>

```chapter-links-errors
  [JSON]   json-encode-err   json-decode-err
  [JSON8]  json8-encode-err   json8-decode-err
  [Packle] packle-encode-err   packle-decode-err   
  [UTF8]   bad-byte   expected-start   expected-cont
           incomplete-seq   overlong   bad-code-point
```

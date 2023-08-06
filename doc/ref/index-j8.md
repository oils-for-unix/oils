---
in_progress: yes
css_files: ../../web/base.css ../../web/help-index.css ../../web/toc.css
---

Index of J8 Notation Topics
===

These are links to topics in the [Oils Reference](index.html).

Siblings:

- [Index of OSH Topics](index-osh.html)
- [Index of YSH Topics](index-osh.html)

<div id="toc">
</div>

Encoding: All J8 notation is UTF-8.

<h2 id="j8-str">J8 Strings</h2>

These are simply [JSON][] strings with the two J8 Escapes, and the
optional J prefix.

```chapter-links-data-lang
  [JSON Escape]   \u1234    \n
  [J8 Escape]     \yff      \u{123456}
  [J Prefix]      j"hello"
```

<h2 id="json8">JSON8 (Objects)</h2>

This is [JSON][] with the addition of J8 strings.

```chapter-links-data-lang
  [Null]    null
  [Bool]    true    false
  [Int]     1234
  [Float]   3.14159
  [Str]     "foo"   j"NUL \y00"
  [List]    [42, true, {"key": 42}]
  [Dict]    {"name": "bob": "age": 25}
```

<h2 id="tsv8">TSV8 (Tables)</h2>

These are the J8 Primtives (Bool, Int, Float, Str), separated by tabs.

Example:

<pre>
!tsv8    name    age
!type    Str     Int
         Alice   42
         Bob     25
</pre>

```chapter-links-data-lang
  [Gutter]    !type
```

[JSON]: https://json.org/


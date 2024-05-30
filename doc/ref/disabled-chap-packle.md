---
in_progress: yes
all_docs_url: ..
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Packle
======

This chapter in the [Oils Reference](index.html) describes Packle, a binary
serialization format for object graphs.

It's a secure subset of Python's `pickle` format.

Advantages:

- Strings are length-prefixed, so they don't need to be escaped and unescaped.
- Exact float representation, with NaN, Inf, and -Inf values.
- Represent graphs, not just trees.  (Think "JSON key sharing")
- Strict Byte strings and strict Unicode, not the mess of JSON strings.

<div id="toc">
</div>


## Atoms

TODO: describe wire format.

### Null

### Bool

### Int

### Float

### Bytes

### Unicode

## Compound

TODO: describe wire format.

### List

### Dict


[JSON]: https://json.org


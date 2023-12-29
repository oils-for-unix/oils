---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Errors
======

This chapter in the [Oils Reference](index.html) describes **errors**.

<div id="toc">
</div>


## JSON

### json-encode-err

JSON encoding has three possible errors:

1. Object of this type can't be serialized
   - For example, `Str List Dict` are YSH objects can be serialized.
   - But `Eggex Func Range` can't.
1. Circular reference
   - e.g. a Dict that points to itself, a List that points to itself, and other
     permutations
1. Invalid UTF-8 in string, e.g. binary data like `\xfe\xff`
   - Note: we can use the Unicode replacement char to avoid an error.

### json-decode-err

TODO

## JSON8

### json8-encode-err

Compared to JSON, JSON8 removes an encoding error:

3. Invalid UTF-8 is OK, because it gets turned into a binary string like
   `b"byte \yfe\yff"`.

### json8-decode-err

TODO

## Packle Errors

### packle-encode-err

Packle has no encoding errors!

1. TODO: Unserializable `Eggex Func Range` can be turned into "wire Tuple"
   `(type_name: Str, heap_id: Int)`.
   - When you read a packle into Python, you'll get a tuple.
   - When you read a packle back into YSH, you'll get a `value.Tombstone`?
1. Circular references are allowed.  Packle data expresses a **graph**, not a
   tree.
1. Both Unicode and binary data are allowed.

### packle-decode-err

TODO

## UTF8 Errors

This is for reference.

### bad-byte   

### expected-start   

### expected-cont

### incomplete-seq   

### overlong

### bad-code-point

e.g. decoded to something in the surrogate range


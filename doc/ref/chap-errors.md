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
1. Float values of NaN, Inf, and -Inf can't be encoded.
   - TODO: option to use `null` like JavaScript.
1. Invalid UTF-8 in string, e.g. binary data like `\xfe\xff`
   - TODO: option to use the Unicode replacement char to avoid an error.

### json-decode-err

1. The encoded message itself is not valid UTF-8.
   - (Typically, you need to check the unescaped bytes in string literals
     `"abc\n"`).
1. Lexical error, like
   - the message `+`
   - an invalid escape `"\z"` or a truncated escape `"\u1"`
   - A single quoted string like `u''`
1. Grammatical error
   - like the message `}{`
1. Unexpected trailing input
   - like the message `42]` or `{}]`

## JSON8

### json8-encode-err

Compared to JSON, JSON8 removes an encoding error:

5. Invalid UTF-8 is OK, because it gets turned into a binary string like
   `b"byte \yfe\yff"`.

### json8-decode-err

JSON8 has the same decoding errors as JSON, plus:

4. `\u{dc00}` should not be in the surrogate range.  This means it doesn't
   represent a real character, and `\yff` escapes should be used instead.
4. `\yff` should not be in `u''` string.  (It's only valid in `b''` strings.)

## Packle

### packle-encode-err

Packle has no encoding errors!

1. TODO: Unserializable `Eggex Func Range` can be turned into "wire Tuple"
   `(type_name: Str, heap_id: Int)`.
   - When you read a packle into Python, you'll get a tuple.
   - When you read a packle back into YSH, you'll get a `value.Tombstone`?
1. Circular references are allowed.  Packle data expresses a **graph**, not a
   tree.
1. Float values NaN, Inf, and -Inf use their binary representations.
1. Both Unicode and binary data are allowed.

### packle-decode-err

TODO

## UTF8

This is for reference.

### utf8-encode-err

Oils stores strings as UTF-8 in memory, so it doesn't often do encoding.

- Surrogate range?

### utf8-decode-err

#### bad-byte   

#### expected-start   

#### expected-cont

#### incomplete-seq   

#### overlong

I think this is only leading zeros?

Like the difference between `123` and `0123`.

#### bad-code-point

e.g. decoded to something in the surrogate range

Note: I think this is relaxed for WTF-8, and our JSON decoder probably needs to
use it.



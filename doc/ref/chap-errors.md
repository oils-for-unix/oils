---
title: Errors (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Errors**

</div>

This chapter describes **errors** for data languages.  An error checklist is
often a nice, concise way to describe a language.

Related: [Oils Error Catalog, With Hints](../error-catalog.html) describes
errors in code.

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

## UTF8

J8 Notation is built on UTF-8, so let's summarize UTF-8 errors.

### err-utf8-encode

Oils stores strings as UTF-8 in memory, so it doesn't encode UTF-8 often.

But it may have a function to encode UTF-8 from a `List[Int]`.  These errors
would be handled:

1. Integer greater than max code point
1. Code point in the surrogate range

### err-utf8-decode

A UTF-8 decoder should handle these errors:

1. Overlong encoding.  In UTF-8, each code point should be represented with the
   fewest possible bytes. 
   - Overlong encodings are the equivalent of writing the integer `42` as
     `042`, `0042`, `00042`, etc.  This is not allowed.
1. Surrogate code point.  The sequence decodes to a code point in the surrogate
   range, which is used only for the UTF-16 encoding, not for string data.
1. Exceeds max code point.  The sequence decodes to an integer that's larger
   than the maximum code point.
1. Bad encoding.  A byte is not encoded like a UTF-8 start byte or a
   continuation byte.
1. Incomplete sequence.  Too few continuation bytes appeared after the start
   byte.

## J8 String

J8 strings extend [JSON]($xref) strings, and are a primary building block of J8
Notation.

### err-j8-str-encode

J8 strings can represent any string &mdash; bytes or unicode &mdash; so there
are **no encoding errors**.

### err-j8-str-decode

1. Escape sequence like `\u{dc00}` should not be in the surrogate range.
   - This means it doesn't represent a real character.  Byte escapes like
     `\yff` should be used instead.
1. Escape sequence like `\u{110000}` is greater than the maximimum Unicode code
   point.
1. Byte escapes like `\yff` should not be in `u''` string.
   - By design, they're only valid in `b''` strings.

Implementation-defined limit:

4. Max string length (NYI)
   - e.g. more than 4 billion bytes could overflow a length field, in some
     implementations

## J8 Lines

Roughly speaking, J8 Lines are an encoding for a stream of J8 strings.  In
[YSH]($xref), it's used by `@(split command sub)`.

### err-j8-lines-encode

Like J8 strings, J8 Lines have no encoding errors by design.

### err-j8-lines-decode

1. Any error in a J8 quoted string.
   -  e.g. no closing quote, invalid UTF-8, invalid backslash escape, ...
1. A line with a quoted string has extra text after it.
   - e.g. `"mystr" extra`.
1. An unquoted line is not valid UTF-8.

## JSON

### err-json-encode

JSON encoding has these errors:

1. Object of this type can't be serialized.
   - For example, `Str List Dict` are Oils objects can be serialized, but
     `Eggex Func Range` can't.
1. Circular reference.
   - e.g. a Dict that points to itself, a List that points to itself, and other
     permutations
1. Float values of NaN, Inf, and -Inf can't be encoded.
   - (These encode to `null` in Oils, following JavaScript.)

Note that invalid UTF-8 bytes like `0xfe` produce a Unicode replacement
character, not a hard error.

### err-json-decode

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

Implementation-defined limits, i.e. outside the grammar:

5. Integer too big
   - implementations may decode to a 64-bit integer
1. Floats that are too big 
   - may decode to `Inf`
1. Max array length (NYI)
   - e.g. more than 4 billion objects in an array could overflow a length
     field, in some implementations
1. Max object length (NYI)
1. Max depth for arrays and objects (NYI)
   - to avoid a recursive parser blowing the stack

## JSON8

### err-json8-encode

JSON8 has the same encoding errors as JSON.

However, the encoding is lossless by design.  Instead of invalid UTF-8 being
turned into a Unicode replacment character, it can use J8 strings with byte
escapes like `b'byte \yfe\yff'`.

### err-json8-decode

JSON8 has the same decoding errors as JSON, plus J8 string decoding errors.

See [err-j8-str-decode](#err-j8-str-decode).

<!--

## Packle

TODO: Not implemented!

### err-packle-encode

Packle has no encoding errors!

1. TODO: Unserializable `Eggex Func Range` can be turned into "wire Tuple"
   `(type_name: Str, heap_id: Int)`.
   - When you read a packle into Python, you'll get a tuple.
   - When you read a packle back into YSH, you'll get a `value.Tombstone`?
1. Circular references are allowed.  Packle data expresses a **graph**, not a
   tree.
1. Float values NaN, Inf, and -Inf use their binary representations.
1. Both Unicode and binary data are allowed.

### err-packle-decode

TODO

-->


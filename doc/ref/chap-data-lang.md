---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Data Languages
==============

This chapter in the [Oils Reference](index.html) describes data languages: J8
Notation and Packle.

This is a quick reference, not the official spec.

<div id="toc">
</div>


## J8 Strings

<h3 id="json-escape">json-escape <code>\" \n \u1234</code></h3>

- `\" \\`
- `\b \f \n \r \t`
- `\u1234`

### surrogate-pair

Inherited from JSON

See [Surrogate Pair Blog
Post](https://www.oilshell.org/blog/2023/06/surrogate-pair.html).

### j8-escape

- `\yff`
- `\u{03bc} \u{123456}`

<h3 id="b-prefix">b-prefix <code>b""</code></h3>

Used to express byte strings.

- May contain `\yff` escapes, e.g. `b"byte \yff"`
- May **not** contain `\u1234` escapes.  Must be `\u{1234}` or `\u{123456}`


<h3 id="j-prefix">j-prefix <code>j""</code></h3>

Used to express that a string is valid Unicode.  (JSON strings aren't
necessarily valid Unicode: they may contain surrogate halves.)

- No `\yff` escapes
- May **not** contain `\u1234` escapes, must be `\u{1234}` or `\u{123456}`

## JSON8

These are simply [JSON][] strings with the two J8 Escapes, and the
optional J prefix.

### Null   

Expressed as the 4 letters `null`.

### Bool   

Either `true` or `false`.


### Number

See JSON grammar.

If there is a decimal point or `e-10` suffix, then it's decoded into YSH float.

### Json8String

It's one of 3 types:

- JSON string
- B string (bytes)
- J string (unicode)

### List

Known as `array` in JSON

### Dict

Known as `object` in JSON

## TSV8

These are the J8 Primitives (Bool, Int, Float, Str), separated by tabs.


### column-attrs   

```
!tsv8    name    age
!type    Str     Int
         Alice   42
         Bob     25
```

### column-types

The primitives:

- Null
- Bool
- Int
- Float
- Str


# Packle

- Binary data represented length-prefixed without encode/decode
- Exact float representation
- Represent graphs, not just trees.  ("JSON key sharing")


[JSON]: https://json.org


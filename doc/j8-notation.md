---
in_progress: yes
default_highlighter: oils-sh
---

J8 Notation
===========

J8 Notation is a set of interchange formats for **Bytes, Strings, Records, and
Tables**.  It's built on [JSON]($xref), and compatible with it in many ways.

It was designed for Oils, but it is **not** specific to Oils.  This is just
like JSON isn't specific to JavaScript: today a Python program and a Go program
may communicate with [JSON]($xref), and JavaScript isn't involved at all.


<div id="toc">
</div>

## Goals

- Fix the JSON-Unix mismatch: be able to express byte strings.
  - Note: you can still use plain JSON In Oils if **lossy** encodings are OK!
- Provide an option to avoid the Surrogate Pair / UTF-16 legacy of JSON
- Expose some information about strings vs. bytes
- Turn TSV into an **exterior** [data
  frame](https://www.oilshell.org/blog/2018/11/30.html) format.
  - It can represent tabs!  And binary data.

Non-goals:

- "Replace" JSON.  It's upward compatible.
- Resolve strings vs. bytes dilemma in all situations.

## J8 Notation in As Few Words As Possible

J8 Strings are a superset of JSON strings:

Only valid unicode:

<pre style="font-size: x-large;">
u'hi &#x1f926; \u{1f926}'                  &rarr; hi &#x1f926; &#x1f926;
</pre>

JSON: unicode + surrogate halves:

<pre style="font-size: x-large;">
 "hi &#x1f926; \ud83e\udd26"               &rarr; hi &#x1f926; &#x1f926;
 "\ud83e"
</pre>

Any byte string:

<pre style="font-size: x-large;">
b'hi &#x1f926; \u{1f926} \yf0\y9f\ya4\ya6' &rarr; hi &#x1f926; &#x1f926; &#x1f926;
b'\yff'
</pre>

JSON8 is built on top of J8 strings, as well as:

1. Unquoted object/Dict keys `{d, 42}`
1. Trailing commas `{"d": 42,}` and `[42,]`
1. Single-line comments `//` and `#`

TSV8:

1. Required first row with column names
1. Optional second row with column types
1. Gutter Column

## Background

See [ref/toc-data.html](ref/toc-data.html) for the reference.

<!-- TODO: fix CSS -->

It's available in OSH and YSH, but should be implemented in all languages.

### TODO / Diagrams

- Doc: How to Turn a JSON library encoder into a J8 Notation library.  (Issue:
  byte strings vs. unicode strings.  J8 is more expressive.)
- Diagrams of Evolution
  - JSON strings -> J8 Strings
  - J8 strings as a building block for JSON8 and TSV8
- Superset relationships:
  - JSON strings are valid J8 strings
  - which means all JSON is valid JSON8
  - `b''` strings can express a superset of JSON strings, which can express a
    superset of `u''` strings
    - J8-style `u'' b''` strings vs. *J8 strings*
- Venn Diagrams of Data Language Relationships
  - If you add the left "gutter" column, every TSV is valid TSV8.
  - Every TSV8 is also syntactically valid TSV.  For example, you can import it
    into a spreadsheet, and remove/ignore the gutter column and type row.
  - TODO: make a screenshot and test it
- YSH relationships
  - Every J8 string is valid in YSH, with `u''`

## Strings and Bytes

### Review of JSON Strings

```
  [escaped]       \"  \\  \/  \b  \f  \n  \r  \t
  [unicode]       \u1234
```

- Important: JSON strings can't contain literal tabs!  That is good for TSV8.

TODO: Do we need JNUM a name for JSON numbers? 

### J8 strings - Byte strings which may be UTF-8 encoded


```
  [unicode]       \u{123456} to add UTF-8.  No surrogates.
  [byte]          \y00 - because \x00 mistakenly means \u0000
  [escaped]       does adding \' make sense?  Probably not
```

Examples:

```
u'but accepted'  # similar to !json8 and !tsv8 prefixes
b'nul byte \y00, unicode \u{123456}'
'this is a u string, but discouraged?'
```

Compatible form:

- The `j` prefix is present if and only if `\y` or `\u{}` is in the string.

Distinguished form:

- The `j` prefix is always present.

## Tree-Shaped Records

### Review of JSON

See <https://json.org>

```
  [primitive]     null   true   false
  [number]        42  -1.2e-4
  [string]        "hello\n", see J8 Strings
  [array]         [1, 2, 3]
  [object]        {"key": 42}
```

### JSON8 - Records built on J8 strings

Examples:

```
!json8  # optional prefix to distinguish from JSON
{ "name": "Bob",
  "age": 30,
  "signature": j"\y00\y01",
}
```

```
!json8  # on multiple lines
[]

!json8 {}  # on a single line

!json8 [1]

```

TODO: Look at https://json5.org/ extensions as well

- Comments?
- Containers
  - Trailing comma (probably)
  - Unquoted keys (if they're valid identifiers)
    - note that {var: 42} is fine in YSH and YSON
- Strings
  - Single quoted strings like coreutils ls?
  - (NO to line breaks)
- Numbers - I don't see a strong reason for changing these
  - +Inf, -Inf, NaN
  - Numbers can be readable like 1_000_000?  Though this may break tools
  - Hexadecimal?  maybe

Smooth form:

- J8 string are all in Smooth form
- No `!json8` prefix.
- Obeys JSON's stricter syntax
  - no trailing commas
  - comments stripped

Distinguished form

- The `!json8` prefix is present.

Canonical form?  The shortest form?

- Keys aren't quoted?

## Table-Shaped Textual Data

### Review of TSV

See RFC (TODO)

Example:

```
name    age
alice   30
bob     40
```

Restrictions:

- Cells can't contain tabs or newlines.
  - Spaces can be confused with tabs.
- There's no escaping, so unprintable bytes result in an unprintable TSV file.


### TSV8 - Tables built on J8 strings

Example:

```
!tsv8   age     name    
!type   Int     Str     # optional types
!other  x       y       # more column metadata
        30      alice
        40      bob
        50      "a\tb"
        60      j"nul \y00"
```

```
  [Bool]      false   true
  [Int]       same as YSON / YNUM / JNUM
  [Float]     same as YSON / YNUM / JNUM
  [Str]       J8 string
```

- Null Issues:
  - Are bools nullable?  Seems like no reason, but you could be missing
  - Are ints nullable?  In SQL they probably are
  - Are floats nullable?  Yes, like NA in R.
- Empty cell can be equivalent to null?  Or maybe it's better to erxplicit.

More notes:

- It's OK to use plain TSV in YSH programs as well.  You don't have to add
  types if you don't want to.

Smooth Form (not necessarily recommended):

- Cells don't have quotes when not strictly necessary?
  - Then you can import as is.
  - e.g. 'foo/bar.c' is not quoted, and 'Bob C' is not quoted, which matches
    TSV.

Canonical form:

- Types are spelled exactly as Bool, Int, Float, Str
- TODO: What cells should be quoted?  It shouldn't just be identifier names,
  because I don't want to quote `src/myfile.py`.
  - Definitely cells with double quotes `"` (and even single quotes)
  - Definitely NOT alphanumeric and `.-_/`, since those are filename chars.
    - But probably all other punctuation like `+` and `=`.
  - Probably cells with `" "`

TSV8 is always distinguished by leading `!tsv8`.


## FAQ

### Why are byte escapes spelled `\yff` and not `\xff` like C?

Because the JavaScript and Python languages both overload `\xff` to mean
`\u{ff}`.

TODO: example

This is exactly the confusion that J8 notation sets out to fix, so we choose to
be ultra **explicit** and different.

### Why have both `u''` and `b''` strings, if only `b''` are needed?

Oils doesn't have a string/bytes distinction (on the "interior"), but many
languages like Python and Rust do.  Certain apps could make use of the
distinction.

Round-tripping arbitrary JSON strings also involves crazy hacks like WTF-8.
Our `u''` strings don't require WTF-8 because they can't represent surrogate
halves.

`u''` strings add trivial weight to the spec, since they just remove `\yff`
from the valid escapes.

### How Do I Write a J8 Encoder or Decoder?

The list of errors at [ref/chap-errors.html](ref/chap-errors.html) may be a
good starting points.

## Future Work

We could have an SEXP8 format:

- Concrete syntax trees
  - with location information
- Textual IRs like WebAssembly


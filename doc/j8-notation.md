---
in_progress: yes
default_highlighter: oils-sh
---

J8 Notation
===========

J8 Notation is a set of text interchange formats.  It specifies a strict syntax
for **strings** / bytes, tree-shaped **records**, line-based **streams**, and
**tables**.

It's part of the Oils project, and was designed to solve the *JSON-Unix
Mismatch*.  It's backward compatible with [JSON]($xref), and built on it.

But J8 notation isn't only for Oils &mdash; just like JSON isn't only for
JavaScript.  Any language that has a JSON library should also have a J8
library.

<!--
it's **not** specific to Oils.  This is just like JSON isn't specific to
JavaScript.  Today, a Python program and a Go program may communicate with
[JSON]($xref), and JavaScript isn't involved at all.
-->

<div id="toc">
</div>

(Historical note: As of January 2024, J8 Notation replaces the [QSN](qsn.html)
design, which wasn't as consistent with both JSON and YSH code.)

## Quick Picture

<style>
  .uni4 {
    /* color: #111; */
  }
  .dq {
    color: darkred;
  }
  .sq {
    color: #111;
  }
</style>

J8 strings can be written in any of these 3 styles:

<pre style="font-size: x-large;">
 <span class=dq>"</span>hi &#x1f642; \u<span class=uni4>D83D</span>\u<span class=uni4>DE42</span><span class=dq>"</span>      <span class="sh-comment"># JSON-style, with surrogate pair</span>

<span class=sq>b'</span>hi &#x1f642; \yF0\y9F\y99\y82<span class=sq>'</span>  <span class="sh-comment"># Can be ANY bytes, including UTF-8</span>

<span class=sq>u'</span>hi &#x1f642; \u{1F642}<span class=sq>'</span>         <span class="sh-comment"># nice alternative syntax</span>
</pre>

They all denote the same decoded string &mdash; "hi" and two `U+1F642` smiley
faces:

<pre style="font-size: x-large;">
hi &#x1f642; &#x1f642;
</pre>


Why accept two more types of string syntax?

- We want to represent any string that a Unix kernel can emit (`argv` arrays,
  env variables, filenames, file contents, etc.)
  - So encoders can emit `b''` strings to avoid losing information.  
- `u''` strings are like `b''` strings, but they can only express valid
  Unicode.  They can't express arbitrary binary data, and there's no such thing
  as a surrogate pair or half.

We then define JSON8 and TSV8 on top of J8 strings.  (Still to be implemented
in Oils.)

## Goals

1. Fix the **JSON-Unix mismatch**: all text formats should be able to express
   byte strings.
   - In Oils, you'll often use plain JSON, because filenames are often strings.
     But note this is a lossy encoding, and J8 notation avoids that.
1. Provide an option to avoid the surrogate pair / **UTF-16 legacy** of JSON.
1. Expose some information about **strings vs. bytes**.
1. Turn TSV into an **exterior** [data
   frame](https://www.oilshell.org/blog/2018/11/30.html) format.
   - Unix tools like `awk`, `cut`, and `sort` already understand tables
     informally.
   - TSV8 cells can represent arbitrary binary data, including tabs and
     newlines.

Non-goals:

1. "Replace" JSON.  JSON8 is upward compatible, and sometimes the lossy
   encoding is OK.
1. Resolve the strings vs. bytes dilemma in all situations.
   - Like JSON, our spec is **syntactic**.  We don't specify what interior
     types a particular language maps strings to.

<!--
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

## Structured Formats

### JSON8

### TSV8

1. Required first row with column names
1. Optional second row with column types
1. Gutter Column

-->

## Background

See [ref/toc-data.html](ref/toc-data.html) for the reference.

<!-- TODO: fix CSS -->

It's available in OSH and YSH, but should be implemented in all languages.

### TODO / Diagrams

- Diagram of Evolution
  - JSON strings &rarr; J8 Strings
  - J8 strings as a building block &rarr; JSON8 and TSV8
- Venn Diagrams of Data Language Relationships
  - If you add the left "gutter" column, every TSV is valid TSV8.
  - Every TSV8 is also syntactically valid TSV.  For example, you can import it
    into a spreadsheet, and remove/ignore the gutter column and type row.
  - TODO: make a screenshot and test it
- Doc: How to turn a JSON library into a J8 Notation library.
  - Issue: an interior type that can represent byte strings.

## J8 Strings (Unicode and bytes)

### Review of JSON strings

JSON strings may have these escape sequences:

    \"  \\  \/  \b  \f  \n  \r  \t
    \u1234

Properties of JSON:

- The encoded form must also be valid UTF-8.
- The encoded form can't contain literal control characters, including literal
  tabs or newlines.  (This is good, because it allows fast TSV8 parsers to
  count literal tabs and newlines.)

### J8 Description

`b''` strings have these escapes:

    \yff            # byte escape
    \u{1f926}       # code point escape
    \'              # single quote, instead of \"
    \b \f \n \r \t  # same as JSON

`u''` strings have all the same escapes, except for `\yff`.  This implies that
they're always valid unicode strings.  (If JSON-style `\u1234` escapes were
allowed, they wouldn't be.)

Examples:

    u'unicode string \u{1f642}' 
    b'nul byte \y00, unicode \u{1f642}'

A string *without* a prefix, like `'foo'`, is equivalent to `u'foo'`:

     'this is a u string'  # discouraged, unless the context is clear

    u'this is a u string'  # better to be explicit

### What's representable by each style?

<style>
#subset {
    text-align: center;
    background-color: #DEE;
    padding-top: 0.5em; padding-bottom: 0.5em;
    margin-left: 3em; margin-right: 3em;
}
.set {
  font-size: x-large;     
}
</style>

These relationships might help you understand J8 strings:

<div id="subset">

<span class="set">Strings representable by `u''`</span><br/>
&equals; All Unicode Strings (no more and no less)

<b>&subset;</b>

<span class="set">Strings representable by `""`</span> (JSON-style)<br/>
&equals; All Unicode Strings <b>&cup;</b> Surrogate Half Errors

<b>&subset;</b>

<span class="set">Strings representable by `b''`</span></br>
&equals; All Byte Strings

</div>

Examples:

- `"\udd26"` is an invalid string representable with JSON (surrogate half
  error), but not with `u''` strings.
- `b'\yff'` is a byte representable with `b''` strings, but not with JSON
  strings or `u''` strings.

### YSH has 2 of the 3 styles

The `u''` and `b''` strings are valid in YSH code:

    echo u'hi \u{1f642}'

    var myBytes = b'\yff\yfe'

But double-quoted strings are not.  Unfortunately, they can't be reconciled,
because shell strings look like `"x = ${myvar}"` and JSON looks like
`"line\n"`.

### Assymmetry of Encoders and Decoders

A couple things to notice about J8 encoders:

1. They *must* emit `b''` strings to avoid losing information.
   - If they were to emit pure JSON strings, then they'd have to use the
     Unicode replacement char `U+FFFD`, which is lossy.
1. They *never* need to emit `u''` strings.
   - This is because `""` strings can represent all such values.  Still, `u''`
     strings may be useful or desirable in some situations, like when you want
     to assert that a value must be valid Unicode.

On the other hand, J8 decoders must accept all 3 kinds of strings.

## JSON8: Tree-Shaped Records

### Review of JSON

See <https://json.org>

```
  [primitive]     null   true   false
  [number]        42  -1.2e-4
  [string]        "hello\n", see J8 Strings
  [array]         [1, 2, 3]
  [object]        {"key": 42}
```

### JSON8 Description

JSON8 is built on top of J8 strings.  It also allows:

1. Unquoted object/Dict keys `{d: 42}`
1. Trailing commas `{"d": 42,}` and `[42,]`
1. C- and JavaScript-style comments like `//` and `/* */` (not nested)

Examples:

```
!json8  # optional prefix to distinguish from JSON
{ name: "Bob",  // comment
  age: 30,
  signature: b'\y00\y01 ... \yff',
}
```

## J8 Lines - Lines of Text

*J8 Lines* is another format built on J8 strings.

Literal control characters like `\n` are illegal in J8 strings, which means
that they always occupy **one** physical line.

So if you want to represent 4 filenames, you can simply use 4 lines:

      dir/my-filename.txt      # unquoted strings allow . - /
     "dir/with spaces.txt"     # JSON-style
    b'dir/with bytes \ff.txt'  # J8-style
    u'dir/unicode \u{3bc}'

Leading spaces on each line are ignored, because this allows aligning the
quotes.

*J8 Lines* can be viewed as a degenerate case of TSV8, described in the next
section.

### Related

- <https://jsonlines.org/> 
- <https://ndjson.org/> - Newline Delimited JSON

## TSV8: Table-Shaped Text

Row and columns.

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

### TSV8 Description

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

## Summary

This document described an upgrade of JSON strings:

- J8 Strings

And three formats that built on top of these strings:

1. JSON8
1. J8 Lines
1. TSV8

## Appendix

### Related Links

- <https://json.org/>
- <https://json5.org/>
- [JSON with Commas and
  Comments](https://nigeltao.github.io/blog/2021/json-with-commas-comments.html)
- Survey: <https://github.com/json-next/awesome-json-next>

### Future Work

We could have an SEXP8 format for:

- Concrete syntax trees, with location information
- Textual IRs like WebAssembly

## FAQ

### Why are byte escapes spelled `\yff`, and not `\xff` as in C?

Because in JavaScript and Python, `\xff` is a **code point**, not a byte.  That
is, it's a synonym for `\u00ff`.

One of Chrome's JSON encoders [also has this
confusion](https://source.chromium.org/chromium/chromium/src/+/main:base/json/json_reader.h;l=27;drc=d0919138b7951c1a154cf802a68aad7904b6f4c9).

This is exactly what we don't want, and the `\yff` is explicitly different for
that raeson.

### Why have both `u''` and `b''` strings, if only `b''` are needed?

A few reasons:

1. Apps in languages like Python and Rust could make use of the distinction.
   Oils doesn't have a string/bytes distinction (on the "interior"), but many
   languages do.
1. Using `u''` strings can avoid crazy hacks like
   [WTF-8](http://simonsapin.github.io/wtf-8/), which is often required for
   round-tripping arbitrary JSON strings.  Our `u''` strings don't require
   WTF-8 because they can't represent surrogate halves.
1. `u''` strings add trivial weight to the spec, since compared to `b''`
   strings, they simply remove `\yff`.  This works because *encoded* J8 strings
   must be UTF-8 encoded.

### How do I write a J8 encoder or decoder?

The list of errors at [ref/chap-errors.html](ref/chap-errors.html) may be a
good starting point.

## Glossary

- J8 Strings - the building block for JSON8 and TSV8.  There are 3 related
  syntaxes `""` and `b''` and `u''`.
- JSON strings - double quoted strings.
- J8-style strings - either `b''` or `u''`.

Formats built on J8 strings:

- J8 Lines - J8 strings, one per line.
- JSON8 - An upgrade of JSON.
- TSV8 - An upgrade of TSV.



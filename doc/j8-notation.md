---
default_highlighter: oils-sh
---

J8 Notation Fixes the JSON-Unix Mismatch
===========

J8 Notation is a set of text interchange formats.  It's a syntax for:

1. **strings** / bytes
1. tree-shaped **records**
1. line-based **streams**, and
1. **tables**

It's part of the Oils project, and was designed to solve the *JSON-Unix
Mismatch*.  It's backward compatible with [JSON]($xref), and built on top of
it.

But just like JSON isn't only for JavaScript, J8 notation isn't only for Oils.
Any language that has a JSON library should also have a J8 library.

(Historical note: J8 Notation replaced the very similar [QSN](qsn.html) design
in January 2024.  QSN wasn't as consistent with both JSON and YSH code.)

<div id="toc">
</div>

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

There are 3 styles of J8 strings:

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

Why did we add these `u''` and `b''` strings?

- We want to represent any string that a Unix kernel can emit (`argv` arrays,
  env variables, filenames, file contents, etc.)
  - J8 encoders emit `b''` strings to avoid losing information.  
- `u''` strings are like `b''` strings, but they can only express valid
  Unicode strings.  

<!-- They can't express arbitrary binary data, and there's no such thing as a
surrogate pair or half. -->

Starting with J8 strings, we define the "obvious" formats JSON8, J8 Lines, and
TSV8 (still to be fully implemented in Oils.).

Together, these are called *J8 Notation*.

## Goals

1. Fix the **JSON-Unix mismatch**: all text formats should be able to express
   byte strings.
   - Note that it's often OK to use plain JSON in Oils, because filenames are
     often strings.  But JSON is necessarily a lossy encoding, while J8
     notation is lossless.
1. Provide an option to avoid the surrogate pair / **UTF-16 legacy** of JSON.
1. Expose some information about **strings vs. bytes**.
1. Turn TSV into an **exterior** [data
   frame](https://www.oilshell.org/blog/2018/11/30.html) format.
   - Unix tools like `awk`, `cut`, and `sort` already understand tables
     informally.
   - TSV8 cells can represent arbitrary binary data, including tabs and
     newlines.

Non-goals:

1. "Replace" JSON.  JSON8 is backward compatible with JSON, and sometimes the
   lossy encoding is OK.
1. Resolve the strings vs. bytes dilemma in all situations.
   - Like JSON, our spec is **syntactic**.  We don't specify what interior data
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

## Reference

See the [Data Notation Table of Contents](ref/toc-data.html) in the [Oils
Reference](ref/index.html).

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

Let's review JSON strings, and then describe J8 strings.

### Review of JSON strings

JSON strings are enclosed in double quotes, and may have these escape
sequences:

    \"  \\  \/  \b  \f  \n  \r  \t
    \u1234

Properties of JSON:

- The encoded form must also be valid UTF-8.
- The encoded form can't contain literal control characters, including literal
  tabs or newlines.  (This is good, because it allows fast TSV8 parsers to
  count literal tabs and newlines.)

### J8 Description

There are 3 types of J8 strings: JSON strings, `b''` strings, and `u''`
strings.

`b''` strings have these escapes:

    \yff            # byte escape
    \u{1f926}       # code point escape
                    # 16-bit escapes like \u1234 are ILLEGAL
    \'              # single quote, instead of \"
    \b \f \n \r \t  # same as JSON

`u''` strings have all the same escapes, but **not** `\yff`.  This implies that
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

These relationships might help you understand the 3 styles of strings:

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

- The JSON message `"\udd26"` represents a string that's not Unicode &mdash; it
  has a surrogate half error).  This string is **not** representable with `u''`
  strings.
- The J8 message `b'\yff'` represents a byte string.  This string is **not**
  representable with JSON strings or `u''` strings.

### YSH has 2 of the 3 styles

A nice property of Oils is that the `u''` and `b''` strings are valid in YSH
code:

    echo u'hi \u{1f642}'

    var myBytes = b'\yff\yfe'

This is useful for correct code generation, and generally simplifies the
language.

But JSON-style strings aren't valid in YSH.  The two usages of double quotes
can't really be reconciled, because JSON looks like `"line\n"` and shell looks
like `"x = ${myvar}"`.

### Assymmetry of Encoders and Decoders

A few things to notice about J8 **encoders**:

1. They can emit only `""` strings, possibly using the Unicode replacement char
   `U+FFFD`.  This is equivalent to a strict JSON encoder.
1. They *must* emit `b''` strings to avoid losing information.
   - The `U+FFFD` replacement is lossy.
1. They *never* need to emit `u''` strings.
   - This is because `""` strings (and `b''` strings) can represent all such
     values.  Still, `u''` strings may be desirable in some situations, like
     when you want `\u{1f642}` escapes, or to assert that a value must be a
     valid Unicode string.

On the other hand, J8 **decoders** must accept all 3 kinds of strings.

## JSON8: Tree-Shaped Records

Now that we've defined J8 strings, we can define JSON8, an obvious extension of
JSON.

### Review of JSON

See <https://json.org>

    [primitive]     null   true   false
    [number]        42  -1.2e-4
    [string]        "hello\n"
    [array]         [1, 2, 3]
    [object]        {"key": 42}

### JSON8 Description

JSON8 is like JSON, but:

1. All strings can be J8 strings, i.e. one of the **3 styles** describe above.
1. Object/Dict keys may be **unquoted** `{d: 42}`
   - Unquoted keys must be a valid JS identifier name matching the pattern
     `[a-zA-Z_][a-zA-Z0-9_]*`.
1. **Trailing commas** are allowed on objects and arrays: `{"d": 42,}` and `[42,]`
1. C- and JavaScript-style single-line **comments** like `//`
   - (No block comments, and no `#` comments)

Example:

```
{ name: "Bob",  // comment
  age: 30,
  signature: b'\y00\y01 ... \yff',
}
```

<!--
!json8  # optional prefix to distinguish from JSON

I think using unquoted keys is a good enough signal, or MIME type.

-->

## J8 Lines - Lines of Text

*J8 Lines* is another format built on J8 strings.

Literal control characters like newlines are illegal in J8 strings, which means
that they always occupy **one** physical line.

So if you want to represent 4 filenames, you can simply use 4 lines:

      dir/my-filename.txt       # unquoted string is JS name and . - /
     "dir/with spaces.txt"      # JSON-style
    b'dir/with bytes \yff.txt'  # J8-style
    u'dir/unicode \u{3bc}'

Leading spaces on each line are ignored, which allows aligning the quotes.

Trailing space is also ignored, to aid readability.  That is, significant
spaces must appear in quotes.

*J8 Lines* can be viewed as a degenerate case of TSV8, described in the next
section.

### Related

- <https://jsonlines.org/> 
- <https://ndjson.org/> - Newline Delimited JSON

## TSV8: Table-Shaped Text

Let's review TSV, and then describe TSV8.

### Review of TSV

TSV has a very short specification:

- <https://www.iana.org/assignments/media-types/text/tab-separated-values>

Example:

```
name<TAB>age
alice<TAB>44
bob<TAB>33
```

Limitations:

- Fields can't contain tabs or newlines.
- There's no escaping, so unprintable bytes result in an unprintable TSV file.
- Spaces can be confused with tabs.

### TSV8 Description

TSV8 is like TSV with:

1. A `!tsv8` prefix and required column names.
2. An optional `!type` line, with types `Bool Int Float Str`.
3. Other optional column attributes.
4. Rows with an empty "gutter" column.

Example:

```
!tsv8   age     name    
!type   Int     Str     # optional types
!other  x       y       # more column metadata
        44        alice
        33        bob
         1       "a\tb"
         2      b'nul \y00'
         3      u'unicode \u{3bc}'
```

Types:

```
  [Bool]      false   true
  [Int]       JSON numbers, restricted to [0-9]+
  [Float]     same as JSON
  [Str]       J8 string (any of the 3 styles)
```

Rules for cells:

1. They can be any of 4 forms in J8 Lines:
   1. Unquoted
   1. JSON-style `""`
   1. `u''`
   1. `b''`
1. Leading and trailing whitespace must be stripped, as in J8 Lines.

TODO: What about empty cells?  Are they equivalent to `null`?  TSV apparently
can't have empty cells, as the rule is `[character]+`, not `[character]+`.

### Design Notes

TODO: This section will be filled in as we implement TSV8.

- Null Issues:
  - Are bools nullable?  Seems like no reason, but you could be missing
  - Are ints nullable?  In SQL they probably are
  - Are floats nullable?  Yes, like NA in R.
  - Decoders can use a parallel typed column for nullability?

- It's OK to use plain TSV in YSH programs as well.  You don't have to add
  types if you don't want to.


## Summary

This document described an upgrade of JSON strings:

- J8 Strings - 3 styles

And three formats that built on top of these strings:

- JSON8 - tree-shaped records
- J8 Lines
- TSV8 - table-shaped data

## Appendix

### Related Links

- <https://json.org/>
- JSON extensions
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
is, it's a synonym for `\u00ff`, which is encoded in UTF-8 as the 2 bytes `0xc3
0xbf`.

This is **exactly** the confusion we want to avoid, so `\yff` is explicitly
different.

One of Chrome's JSON encoders [also has this
confusion](https://source.chromium.org/chromium/chromium/src/+/main:base/json/json_reader.h;l=27;drc=d0919138b7951c1a154cf802a68aad7904b6f4c9).

### Why have both `u''` and `b''` strings, if only `b''` is technically needed?

A few reasons:

1. Apps in languages like Python and Rust could make use of the distinction.
   Oils doesn't have a string/bytes distinction (on the "interior"), but many
   languages do.
1. Using `u''` strings can avoid hacks like
   [WTF-8](http://simonsapin.github.io/wtf-8/), which is often required for
   round-tripping arbitrary JSON messages.  Our `u''` strings don't require
   WTF-8 because they can't represent surrogate halves.
1. `u''` strings add trivial weight to the spec, since compared to `b''`
   strings, they simply remove `\yff`.  This is true because *encoded* J8 strings
   must be valid UTF-8.

### How do I write a J8 encoder or decoder?

The list of errors at [ref/chap-errors.html](ref/chap-errors.html) may be a
good starting point.

TODO: describe the Oils implementatino.

## Glossary

- **J8 Strings** - the building block for JSON8 and TSV8.  There are 3 similar
  syntaxes: `"foo"` and `b'foo'` and `u'foo'`.
- **JSON strings** - double quoted strings `"foo"`.
- **J8-style strings** - either `b'foo'` or `u'foo'`.

Formats built on J8 strings:

- **J8 Lines** - unquoted and J8 strings, one per line.
- **JSON8** - An upgrade of JSON.
- **TSV8** - An upgrade of TSV.



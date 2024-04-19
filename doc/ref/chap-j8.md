---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

JSON / J8 Notation
==================

This chapter in the [Oils Reference](index.html) describes [JSON]($xref), and
its **J8 Notation** superset.

See the [J8 Notation](../j8-notation.html) doc for more background.  This doc
is a quick reference, not the official spec.

<div id="toc">
</div>


## J8 Strings

J8 strings are an upgrade of JSON strings that solve the *JSON-Unix Mismatch*.

That is, Unix deals with byte strings, but JSON can't represent byte strings.

<h3 id="json-string">json-string <code>"hi"</code></h3>

All JSON strings are valid J8 strings!

This is important.  Encoders often emit JSON-style `""` strings rather than
`u''` or `b''` strings.

Example:

    "hi μ \n"

<h3 id="json-escape">json-escape <code>\" \n \u1234</code></h3>

As a reminder, the backslash escapes valid in [JSON]($xref) strings are:

    \" \\
    \b \f \n \r \t
    \u1234

Additional J8 escapes are valid in `u''` and `b''` strings, described below.

<h3 id="surrogate-pair">surrogate-pair <code>\ud83e\udd26</code></h3>

JSON's `\u1234` escapes can't represent code points above `U+10000` or
2<sup>16</sup>, so JSON also has a "surrogate pair hack".

That is, there are special code points in the "surrogate range" that can be
paired to represent larger numbers.

See the [Surrogate Pair Blog
Post](https://www.oilshell.org/blog/2023/06/surrogate-pair.html) for an
example:

    "\ud83e\udd26"

Because JSON strings are valid J8 strings, surrogate pairs are also part of J8
notation.  Decoders must accept them, but encoders should avoid them.

You can emit `u'\u{1f926}'` or `b'\u{1f926}'` instead of `"\ud83\udd26"`.

<h3 id="u-prefix">u-prefix <code>u'hi'</code></h3>

A type of J8 string.

    u'hi μ \n'

It's never necessary to **emit**, but it can be used to express that a string
is **valid Unicode**.  JSON strings can represent strings that aren't Unicode
because they may contain surrogate halves.

In contrast, `u''` strings can only have escapes like `\u{1f926}`, with no
surrogate pairs or halves.

- The **encoded** bytes must be valid UTF-8, like JSON strings.
- The **decoded** bytes must be valid UTF-8, **unlike** JSON strings.

Escaping:

- `u''` strings may **not** contain `\u1234` escapes.  They must be `\u{1234}`,
  `\u{1f926}`
- They may not contain `\yff` escapes, because those would represent a string
  that's not UTF-8 or Unicode.
- Surrogate pairs are never necessary in `u''` or `b''` strings.  Use the
  longer form `\u{1f926}`.
- You can always emit literal UTF-8, so `\u{1f926}` escapes aren't strictly
  necessary.  Decoders must accept these escapes.
- A literal single quote is escaped with `\'`
  - Decoders still accept `\"`, but encoders don't emit it.

<h3 id="b-prefix">b-prefix <code>b'hi'</code></h3>

Another J8 string.  These `b''` strings are identical to `u''` strings, but
they can also `\yff` escapes.

Examples:

    b'hi μ \n'
    b'this isn\'t a valid unicode string \yff\fe \u{3bc}'

<h3 id="j8-escape">j8-escape<code>\u{1f926} \yff</code></h3>

To summarize, the valid J8 escapes are:

    \'
    \yff   # only valid in b'' strings
    \u{3bc} \u{1f926} etc.

<h3 id="no-prefix">no-prefix <code>'hi'</code></h3>

Single-quoted strings without a `u` or `b` prefix are implicitly `u''`.

    u'hi μ \n'  
     'hi μ \n'  # same as above, no \yff escapes accepted

They should be avoided in contexts where `""` strings may also appear, because
it's easy to confuse single quotes and double quotes.

## J8 Lines

"J8 Lines" is a format built on top of J8 strings.  Each line is either:

1. An unquoted string, which must be valid UTF-8
2. A quoted J8 string (JSON style `""` or J8-style `b'' u'' ''`)
3. An **ignored** empty line

In all cases, leading and trailing whitespace is ignored.

### unquoted-line

Any line that doesn't begin with `"` or `b'` or `u'` is an unquoted line.
Examples:

    foo bar
    C:\Program Files\
    internal "quotes" aren't special

In contrast, these are quoted lines, and must be valid J8 strings:

    "json-style J8 string"
    b'this is b style'
    u'this is u style'
    
## JSON8

JSON8 is JSON with 4 more things allowed:

1. J8 strings in addition to JSON strings
1. Comments
1. Unquoted keys (TODO)
1. Trailing commas (TODO)

### json8-num

Decoding detail, specific to Oils:

If there's a decimal point or `e-10` suffix, then it's decoded into YSH
`Float`.  Otherwise it's a YSH `Int`.

    42       # decoded to Int
    42.0     # decoded to Float
    42e1     # decoded to Float
    42.0e1   # decoded to Float

### json8-str

JSON8 strings are exactly J8 strings:

<pre>
"hi &#x1f926; \u03bc"
u'hi &#x1f926; \u{3bc}'
b'hi &#x1f926; \u{3bc} \yff'
</pre>

### json8-list

Like JSON lists, but can have trailing comma.  Examples:

    [42, 43]
    [42, 43,]   # same as above

### json8-dict

Like JSON "objects", but:

- Can have trailing comma.
- Can have unquoted keys, as long as they're an identifier.

Examples:

    {"json8": "message"}
    {json8: "message"}     # same as above
    {json8: "message",}    # same as above

### json8-comment

End-of-line comments in the same style as shell:

    {"json8": "message"}   # comment

## TSV8

These are the J8 Primitives (Bool, Int, Float, Str), separated by tabs.


### column-attrs   

```
!tsv8    name    age
!type    Str     Int
!other   x       y
         Alice   42
         Bob     25
```

### column-types

The primitives:

- Bool
- Int
- Float
- Str

Note: Can `null` be in all cells?  Maybe except `Bool`?

It can stand in for `NA`?

[JSON]: https://json.org


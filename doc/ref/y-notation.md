---
in_progress: yes
css_files: ../../web/base.css ../../web/help-index.css ../../web/toc.css
---

Y Notation - Let's Be Precise About Text
==========

Y Notation is a set of interchange formats for **Bytes, Strings, Records, and
Tables**.  It's built on JSON, and compatible with it in many ways.

<!-- TODO: fix CSS -->

Y Notation is a collection of interchange formats, built on top of JSON.

It's available in OSH and YSH, but should be implemented in all languages.

TODO:

- Doc: How to Turn a JSON library encoder into a Y Notation library.  (Issue:
  byte strings vs. unicode strings.  YSTR is more expressive.)
- Diagrams of Evolution: JSON/JSTR -> YSTR/YSON/YTSV
- Venn Diagrams of Data Language Relationships
  - Every JSTR is valid YSTR
  - Every JSON is valid YSON
  - If you add the left "gutter" column, every TSV is valid YTSV.
  - Every YTSV is also syntactically valid TSV.  For example, you can import it
    into a spreadsheet, and remove/ignore the gutter column and type row.
  - TODO: make a screenshot and test it
- YSH relationships
  - Every YSTR is valid in YSH
  - YSON with YSTR in **distinguished form** is valid in YSH
    - `"$foo"` is something different in shell, so we need `y"$foo"`.

## Review of JSON

See <https://json.org>

```oil-help-topics
  [primitive]     null   true   false
  [number]        42  -1.2e-4
  [string]        "hello\n", see JSTR
  [array]         [1, 2, 3]
  [object]        {"key": 42}
```

### JSTR is a name for JSON strings

```oil-help-topics
  [escaped]       \"  \\  \/  \b  \f  \n  \r  \t
  [unicode]       \u1234
```

- Important: JSTR can't contain literal tabs!  That is good for YTSV.

TODO: Do we need JNUM a name for JSON numbers? 

## YSTR - Byte strings which may be UTF-8 encoded

```oil-help-topics
  [unicode]       \u{123456} to add UTF-8.  No surrogates.
  [byte]          \y00 - because \x00 mistakenly means \u0000
  [escaped]       does adding \' make sense?  Probably not
```

Examples:

```
"no y prefix needed"
y"but accepted"  # similar to !yson and !ytsv prefixes
y"nul byte \y00, unicode \u{123456}"
```

Smooth form:

- The `y` prefix is present if and only if `\y` or `\u{}` is in the string.

Distinguished form:

- The `y` prefix is always present.

## YSON - Records built on YSTR

Examples:

```
!yson  # optional prefix to distinguish from JSON
{ name: "Bob",
  age: 30,
  signature: y"\y00\y01",
}
```

```
!yson  # on multiple lines
[]

!yson {}  # on a single line

!yson [1]

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

- YSTR are all in Smooth form
- No `!yson` prefix.
- Obeys JSON's stricter syntax
  - no trailing commas
  - comments stripped

Distinguished form

- The `!yson` prefix is present.

Canonical form?  The shortest form?

- Keys aren't quoted?

## Review of TSV

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


## YTSV - Tables built on YSTR

Example:

```
!ytsv   age     name    
!type   Int     Str     # optional types
!other  x       y       # more column metadata
        30      alice
        40      bob
        50      "a\tb"
        60      y"nul \y00"
```

```oil-help-topics
  [Bool]      false   true
  [Int]       same as YSON / YNUM / JNUM
  [Float]     same as YSON / YNUM / JNUM
  [Str]       YSTR
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

YTSV is always distinguished by leading `!ytsv`.

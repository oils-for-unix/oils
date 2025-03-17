---
in_progress: yes
default_highlighter: oils-sh
---

HTM8 - An Easy Subset of HTML5, With Some Errors
=================================

HTM8 is a data language, which is part of J8 Notation:

- It's a subset of HTML5, so there are **Syntax Errors**
  - It's "for humans"
  - `<li><li>` example
- It's Easy
  - Easy to Implement - ~700 lines of regular languages and Python
  - And thus Easy to Remember, for users
  - Runs Efficiently - you don't have to materialize a big DOM tree, which
    causes many allocations
- Convertible to XML?
  - without allocations, with a `sed`-like transformation!
  - low level lexing and matching
- Ambitious
  - zero-alloc whitelist-based HTML filter for user content
  - zero-alloc browser and CSS-style content queries

Currently, all of Oils docs are parsed and processed with it.

We would like to "lift it up" into an API for YSH users.

<!--

TODO: 99.9% of HTML documents from CommonCrawl should be convertible to XML,
and then validated by an XML parser

- lxml - this is supposed to be high quality

- Python stdlib uses expat - https://libexpat.github.io/

- Gah it's this huge thing, 8K lines: https://github.com/libexpat/libexpat/blob/master/expat/lib/xmlparse.c
  - do they have the billion laughs bug?

-->

<div id="toc">
</div> 

## Structure of an HTM8 Doc

### Tags - Open, Close, Self-Closing

1. Open `<a>`
1. Close `</a>`
1. StartEnd `<img/>`

HTML5 doesn't have the notion of self-closing tags.  Instead, it silently ignores
the trailing `/`.

We are bringing it back for human, because we think it's too hard for people to
remember the 16 void elements.

And lack of balanced bugs causes visual bugs that are hard to debug.  It would
be better to get an error **earlier**.

### Attributes - Quotes optional

5 closely related Syntaxes

1. Missing `<a missing>`
1. Empty `<a empty=>`
1. Unquoted `<a href=foo>`
1. Double Quoted `<a href="foo">`
1. Single Quoted `<a href='foo'>`

Note: `<a href=/>` is disallowed because it's ambiguous.  Use `<a href="/">` or
`<a href=/ >` or `<a href= />`.

### Text - Regular or CDATA

#### Regular Text

- Any UTF-8 text.
- Generally, `& < > " '` should be escaped as `&amp; &lt; &gt; &quot; &apos`.

But we are lenient and allow raw `>` between tags:

    <p> foo > bar </p>

and raw `<` inside tags:

    <span foo="<" > foo </span>

#### CDATA

Like HTML5, we support explicit `<![CDATA[`, even though it's implicit in the
tags.

### Escaped Chars - named, decimal, hex

1. `&amp;` - named
1. `&#999;` - decimal
1. `&#xff;` - hex


### Comments - HTML or XML

1. `<!-- -->`
1. `<? ?>` (XML processing instruction)

### Declarations - HTML or XML

- `<!DOCTYPE html>` from HTML5
- `<?xml version= ... ?>` from XML - this is a comment / processing instruction

## Special Rules For Specific HTML Tags

### `<script>` and `<style>` are Leaf Tags with Special Lexing

- `<script> <style>`

Note: we still have CDATA for compatibility.

### 16 VOID Tags Don't Need Close Tags (Special Parsing)

- `<source> ...`


## Errors

### Notes on Leniency

Angle brackets:

- `<a foo="<">` is allowed, but `<a foo=">">` is disallowed
- `<p> 4>3 </p>` is allowed, but `<p> 4<3 </p>` is disallowed

This makes lexing the top-level structure easier.

- unescaped `&` is allowed, unlike XML
  - it's very common in `<a href="?foo=42&bar=99">`
  - It's lexed as BadAmpersand, in case you want to fix it for XML.  Although
    we don't do that for < and > consistently.

### What are some examples of syntax errors?

- HTM8 tags must be balanced to convert them to XML

- `<script></SCRIPT>` isn't matched
  - the begin and end tags must match exactly, like `<SCRipt></SCRipt>`
  - likewise for `<style>`

- NUL bytes aren't allowed - currently due to re2c sentinel.  Two options:
  1. Make it a syntax error - like JSON8
  1. we could have a reprocessing pass to convert it to the Unicode replacement
     char?  I think that HTML might mandate that
- Encodings other than UTF-8.  HTM8 is always UTF-8.
- Unicode Tag names and attribute names.
  - This is allowed in HTML5 and XML.
  - We leave those out for simpler lexing.  Text and attribute values may be unicode.

- `<a href=">">` - no literal `>` inside quotes
  - HTML5 handles it, but we want to easily scan the "top level" structure of the doc
  - And it doesn't appear to be common in our testdata
  - TODO: we will handle `<a href="&">`

HTML notes:

There are 5 kinds of tags:

- Normal HTML tags
- RCDATA for `<title> <textarea>`
- RAWTEXT `<style> <xmp> <iframe>` ?

and we have

- CDATA `<script>`
  - TODO: we need a test case for `</script>` in a string literal?
- Foreign `<math> <svg>` - XML rules

## Under the Hood - Regular Languages, Algebraic Data Types

That is, we use exhaustive reasoning

It's meant to be easy to implement.

### 2 Layers of Lexing

1. TagLexer
1. AttrLexer

### 4 Regular Expressions

Using re2c as the "choice" primitive.

1. Lexer
1. NAME lexer
1. Begin VALUE lexer
1. Quoted value lexer - for decoding `<a href="&amp;">`

## XML Parsing Mode

- Set `NO_SPECIAL_TAGS` - get rid of special cases fo `<script>` and `<style>`

Conflicts between HTML5 and XML:

- In XML, `<source>` is like any tag, and must be closed,
- In HTML, `<source>` is a VOID tag, and must NOT be closedlike any tag, and must be closed,

- In XML, `<script>` and `<style>` don't have special treatment
- In HTML, they do

- The header is different - `<!DOCTYPE html>` vs.  `<?xml version= ... ?>`

- HTML: `<a empty= missing>` is two attributes
- right now we don't handle `<a empty = "missing">` as a single attribute
  - that is valid XML, so should we handle it?

## Algorithms

### What Do You Use This for?

- Stripping comments
- Adding TOC
- Syntax highlighting code
- Adding links shortcuts
- ul-table

TODO:

- DOM API  on top of it
  - node.elementsByTag('p')
  - node.elementsByClassName('left')
  - node.elementByID('foo')
  - innerHTML() outerHTML()
  - tag attrs
  - low level:
    - outerLeft, outerRight, innerLeft, innerRight
- CSS Selectors - `querySelectorAll()`
- sed-like model


### List of Algorithms

- Lexing/Parsing
  - lex just the top level
  - lex both levels
  - match tags - this is the level for value.Htm8Frag?
- sed-like
  - convert to XML!
  - sed-like replacement of DOM Tree or element - e.g. Oils TOC 
- Structured
  - convert to DOMTree
  - lazy selection by tag, or attr (id= and class=)
  - lazy selection by CSS selector expression
  - untrusted HTML filter, e.g. like StackOverflow / Reddit
    - this is Safe HTM8
    - should have a zero alloc way to support this, with good errors?
      - I think most of them silently strip data

### Emitting HTM8 as HTML5

Just emit it!  This always works, by design.

### Converting to XML

- Add quotes to unquoted attributes
  - single and double quotes stay the same?
- Quote special chars - in text, and inside single- and double-quoted attr values
  - & BadAmpersand -> `&amp;`
  - < BadLessThan -> `&lt;`
  - > BadGreaterTnan -> `&gt;`
- `<script>` and `<style>`
  - either add `<![CDATA[`
  - or simply escape their values with `&amp; &lt;`
- what to do about case-insensitive tags?
  - maybe you can just normalize them
  - because we do strict matching
- Maybe validate any other declarations, like `<!DOCTYPE foo>`
- Add XML header `<?xml version=>`, remove `<!DOCTYPE html>`

## Related

- [ysh-doc-processing.html](ysh-doc-processing.html)
- [table-object-doc.html](table-object-doc.html)


## Brainstorming / TODO

### Foreign XML with `<svg>` and `<math>` ?

`<svg>` and `<math>` are foreign XML content.

We might want to support this.

- So I can just switch to XML mode in that case
- TODO: we need a test corpus for this!
- maybe look for wikipedia content
- can we also just disallow these?  Can you make these into external XML files?

This is one way:

    <object data="math.xml" type="application/mathml+xml"></object>
    <object data="drawing.xml" type="image/svg+xml"></object>

Then we don't need special parsing?

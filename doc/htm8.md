---
in_progress: yes
default_highlighter: oils-sh
---

HTM8 - An Easy Subset of HTML5, With Errors
=================================

- Syntax Errors: It's a Subset
- Easy
  - Easy to Remember
  - Easy to Implement
  - Runs Efficiently - you don't have to materialize a big DOM tree, which
    causes many allocations
- Convertable to XML?
  - without allocations, with a `sed`-like transformation!
  - low level lexing and matching

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

## Basic Structure

### Text Content

Anything except `&` and `<`.

These must be `&amp;` and `&lt;`.

`>` is allowed, or you can escape it with `&gt;`.

### 3 Kinds of Character Code

1. `&amp;` - named
1. `&#999;` - decimal
1. `&#xff;` - hex

### 3 Kinds of Tag

1. Start
1. End
1. StartEnd

### 2 Kinds of Attribute

1. Unquoted
1. Quoted

### 2 Kinds of Comment

1. `<!-- -->`
1. `<? ?>` (XML processing instruction)


## Special Rules, From HTML

### 2 Tags Cause Special Lexing

- `<script> <style>`

Note: we still have CDATA for compatibility.


### 16 VOID Tags Change Parsing

- `<source> ...`

### Bonus: XML Mode

- Get rid  of the 2 special lexing tags, and 16 VOID tags

Then you can query HTML


## Under the Hood

### 3 Layers of Lexing

1. Tag
1. Attributes within a Tag
1. Quoted Value for Attributes

## What Do You Use This for?

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

## Algorithms

### Emitting HTM8 as HTML5

Just emit it!  This always works, by design.

### Parsing XML

- Set `NO_SPECIAL_TAGS`


Conflicts between HTML5 and XML:

- In XML, `<source>` is like any tag, and must be closed,
- In HTML, `<source>` is a VOID tag, and must NOT be closedlike any tag, and must be closed,

- In XML, `<script>` and `<style>` don't have special treatment
- In HTML, they do

- The header is different - `<!DOCTYPE html>` vs.  `<?xml version= ... ?>`

- HTML: `<a empty= missing>` is two attributes
- right now we don't handle `<a empty = "missing">` as a single attribute
  - that is valid XML, so should we handle it?

### Converting to XML?

- Add quotes to unquoted attributes
  - single and double quotes stay the same?
- Quote special chars
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

## Leniency

Angle brackets:

- `<a foo="<">` is allowed, but `<a foo=">">` is disallowed
- `<p> 4>3 </p>` is allowed, but `<p> 4<3 </p>` is disallowed

This makes lexing the top-level structure easier.

- unescaped `&` is allowed, unlike XML
  - it's very common in `<a href="?foo=42&bar=99">`
  - It's lexed as BadAmpersand, in case you want to fix it for XML.  Although
    we don't do that for < and > consistently.


## Related

- [ysh-doc-processing.html](ysh-doc-processing.html)
- [table-object-doc.html](table-object-doc.html)

## FAQ

### What Doesn't This Cover?

- HTM8 tags must be balanced to convert them to XML

- NUL bytes aren't allowed - currently due to re2c sentinel
  - Although I think we could have the preprocessing pass to convert it to the
    Unicode replacement char?  I think that HTML might mandate that
- Encodings other than UTF-8.  HTM8 is always UTF-8.
- Unicode Tag names and attribute names.
  - This is allowed in HTML5 and XML.
  - We leave those out for simpler lexing.  Text and attribute values may be unicode.

- `<a href=">">` - no literal `>` inside quotes
  - HTML5 handles it, but we want to easily scan the "top level" structure of the doc
  - And it doesn't appear to be common in our testdata
  - TODO: we will handle `<a href="&">`

There are 5 kinds of tags:

- Normal HTML tags
- RCDATA for `<title> <textarea>`
- RAWTEXT `<style> <xmp> <iframe>` ?

and we have

- CDATA `<script>`
  - TODO: we need a test case for `</script>` in a string literal?
- Foreign `<math> <svg>` - XML rules

## TODO

- `<svg>` and `<math>` are foreign XML content?  Doh
  - So I can just switch to XML mode in that case
  - TODO: we need a test corpus for this!
  - maybe look for wikipedia content
- can we also just disallow these?  Can you make these into external XML files?

This is one way:

    <object data="math.xml" type="application/mathml+xml"></object>
    <object data="drawing.xml" type="image/svg+xml"></object>

Then we don't need special parsing?


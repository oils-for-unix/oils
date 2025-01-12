---
in_progress: yes
default_highlighter: oils-sh
---

HTM8 - Efficient HTML with Errors
=================================

- Syntax Errors: It's a Subset
- Efficient
  - Easy to Remember
  - Easy to Implement
  - Runs Efficiently - you don't have to materialize a big DOM tree, which
    causes many allocations

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

### Converting to XML?

- Always quote all attributes
- Always quote `>` - are we alloxing this in HX8?
- Do something with `<script>` and `<style>`
  - I guess turn them into normal tags, with escaping?
  - Or maybe just disallow them?
- Maybe validate any other declarations, like `<!DOCTYPE foo>`
- Add XML header `<?xml version=>`, remove `<!DOCTYPE html>`

## Related

- [ysh-doc-processing.html](ysh-doc-processing.html)
- [table-object-doc.html](table-object-doc.html)

## FAQ

### What Doesn't This Cover?

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


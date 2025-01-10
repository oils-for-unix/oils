---
in_progress: yes
default_highlighter: oils-sh
---

Doc Processing in YSH - Notation, Query, Templating
====================================================

This is a slogan for "maximalist YSH" design:

*Documents, Objects, and Tables - HTML, JSON, and CSV* &dagger;

This design doc is about the first part - **documents** and document processing.

&dagger; from a paper about the C# language

<div id="toc">
</div> 

## Intro 

Let's sketch a design for 3 aspects of doc processing:

1. HTM8 Notation - A **subset** of HTML5 meant for easy implementation, with
   regular languages.
   - It's part of J8 Notation (although it does not use J8 strings, like JSON8
     and TSV8 do.)
   - It's very important to understand that this is HTM8, not HTML8!
1. A subset of CSS for querying
1. Templating in the Markaby style (a bit like Lisp, but unlike JSX templates)

The basic goal is to write ad hod HTML processors.

YSH programs should loosely follow the style of the DOM API in web browsers,
e.g.  `document.querySelectorAll('table#mytable')` and the doc fragments it
returns.

Note that the DOM API is not available in node.js or Deno by default, much less
any alternative lightweight JavaScript runtimes.

I believe we can write include something that's simpler, and just as powerful,
in YSH.

## Use Cases for HTML Processing

These will help people get an idea.

1. making Oils cross-ref.html
   - query and replacement
1. table language - md-ul-table
   - query and replacement
   - many tables to make here
1. safe HTML subset, e.g. for publishing user results on continuous build
   - well I think I want to encode the policy, like
   - query

Design goals:

- Simple format that can be re-implemented anywhere
  - a few re2c expressions
- Fast
  - re2c uses C
  - Few allocations
- much simpler than an entire browser engine

## Operations

- `doc('<p>')` - validates it and creates a value.Obj
- `docQuery(mydoc, '#element')` - does a simple search

Constructors:

    doc {  # prints valid HT8
      p {
        echo 'hi'
      }
      p {
        'hi'  # I think I want to turn on this auto-quote feature
      }
      raw '<b>bold</b>'
    }

And then

    doc (&mydoc) {  # captures the output, and creates a value.Obj
      p {
        'hi'  # I think I want to turn on this auto-quote feature
        "hi $x"
      }
    }

This is the same as the table constructor

Module:

    source $LIB_YSH/doc.ysh

    doc (&d) {
    }
    doc {
    }
    doc('<p>')

    This can have both __invoke__ and __call__

    var results = d.query('#a')

    # The doc could be __invoke__ ?
    d query '#a' {
    }

    doc query (d, '#a') {
      for result in (results) {
        echo hi
      }
    }

    # we create (old, new) pairs?
    # this is performs an operation like:
    # d.outerHTML = outerHTML
    var d = d.replace(pairs)


Safe HTML subset

    d query (tags= :|a p div h1 h2 h3|) {
      case (_frag.tag) {
        a {
          # get a list of all attributes
          var attrs = _frag.getAttributes()
        }
      }
    }

If you want to take user HTML, then you first use an HTML5 -> HT8 converter.

## Algorithms

### Emitting HX8 as HTML5

Just emit it!  This always work.

### Converting HX8 to XML

- Always quote all attributes
- Always quote `>` - are we alloxing this in HX8?
- Do something with `<script>` and `<style>`
  - I guess turn them into normal tags, with escaping?
  - Or maybe just disallow them?
- Maybe validate any other declarations, like `<!DOCTYPE foo>`
- Add XML header `<?xml version=>`, remove `<!DOCTYPE html>`

## Related

- [table-object-doc.html](table-object-doc.html)

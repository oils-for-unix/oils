---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oil-sh
---

Data Languages
==============

This chapter in the [Oils Reference](index.html) describes data languages: J8
Notation and Packle.

This is a quick reference, not the official spec.

<div id="toc">
</div>


## J8 Strings

<h3 id="json-escape">json-escape \n</h3>

### surrogate-pair

Inherited from JSON

See [Surrogate Pair Blog
Post](https://www.oilshell.org/blog/2023/06/surrogate-pair.html).

<h3 id="j8-escape">j8-escape \yff</h3>

### j-prefix j""


## JSON8

These are simply [JSON][] strings with the two J8 Escapes, and the
optional J prefix.

### Null   

### Bool   

### Int   

### Float aka number

### Str   

### List aka array

### Dict aka object

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



## UTF8 Errors

This is for reference.

### bad-byte   

### expected-start   

### expected-cont

### incomplete-seq   

### overlong

### bad-code-point

e.g. decoded to something in the surrogate range

[JSON]: https://json.org

# Packle

- Binary data represented length-prefixed without encode/decode
- Exact float representation
- Represent graphs, not just trees.  ("JSON key sharing")


---
in_progress: yes
css_files: ../../web/base.css ../../web/help-index.css ../../web/toc.css
---

Data Languages
==============

This chapter in the [Oils Reference](index.html) describes data languages: J8
Notation and Packle.

This is a quick reference, not the official spec.

<div id="toc">
</div>


## J8 Strings

### json-escape \n   

### surrogate-pair

Inherited from JSON

See [Surrogate Pair Blog
Post](https://www.oilshell.org/blog/2023/06/surrogate-pair.html).

### j8-escape \yff   

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

These are the J8 Primtives (Bool, Int, Float, Str), separated by tabs.


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


### bad-start-byte

### bad-cont-byte

### incomplete

### overlong

### bad-code-point

e.g. something in the surrogate range



[JSON]: https://json.org


# Packle

- Binary data represented length-prefixed without encode/decode
- Exact float representation
- Represent graphs, not just trees.  ("JSON key sharing")


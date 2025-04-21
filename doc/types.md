---
default_highlighter: oils-sh
---

Types in the Oils Runtime - OSH and YSH
===========

Here are all types of values in the Oils runtime, organized for understanding.

<div id="toc">
</div> 

## Nine Atoms

Values of these types are immutable:

### Serialiable

- `Null Bool`
- `Int Float` 
- `Str`
  - The only type shared between OSH and YSH.

### More

- `Eggex Match` - to match patterns
- `Range` - to iterate over `3 .. 5`
- `Stdin` - to iterate over lines (has a singleton value)

<!--
It seems like stdin could be a file descriptor, but that doesn't fit with the
shell I/O model.  You always REDIRECT first, then read from stdin.  And you
don't read incrementally from multiple files at once.
-->

<!--

These are variants of VALIDATED strings, with lazily materialized views?

- value.{Htm8,Tsv8,Json8} ?

-->

## Six Containers

- `List Dict` - YSH containers are arbitrarily recursive
- `Place` is for "out parmas"
   - created with `&myvar`, mutated with `call place->setValue(42)`
- `BashArray BashAssoc` are for bash compatibility in OSH:

### `Obj` is for User-defined Types

- `Obj` - has a prototype chain

Objects allow **polymorphism**.  See [YSH Objects](objects.html).

#### Examples of Objects

Modules and types are represented by `Obj` instances of a certain shape, not by
primitive types.

1. Modules are `Obj` instances with attributes, and an `__invoke__` method.
1. Types are `Obj` instances with an `__index__` method, and are often compared
   for identity.

In general, Objects are mutable.  Do not mutate modules or types!

## Five Units of Code

Values of these types are immutable:

- `BoundFunc` (for methods)
- `BuiltinFunc Func`
- `BuiltinProc Proc`

## Four Types for Reflection

- `Command Expr` - custom evaluation of commands and expressions <!-- no CommandFrag, ExprFrag) -->
- `Frame` - a frame on the call stack (`proc` and `func`)
- `DebugFrame` - to trace `eval()` calls, and more

## Appendix

### The JSON Data Model

These types can be serialized to and from JSON:

- `Null Str Int Float List Dict`

### Why Isn't Everything an Object?

In YSH, the `Obj` type is used for **polymorphism** and reflection.

Polymorphism is when you hide **different** kinds of data behind the **same**
interface.

But most shell scripts deal with **concrete** textual data, which may be
JSON-like or TSV-like.  The data is **not** hidden or encapsulated, and
shouldn't be.

### Implementation Details

These types used internally:

- `value.Undef` - used when looking up a variable
- `value.Interrupted` - for SIGINT
- `value.Slice` - for a[1:2]

### Related

- [Types and Methods](ref/chap-type-method.html) in the [Oils
  Reference](ref/index.html)
- [core/value.asdl]($oils-src)


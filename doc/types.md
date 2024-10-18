---
default_highlighter: oils-sh
---

Types in the Oils Runtime - OSH and YSH
===========

Here are all types of values in the Oils runtime, organized for understanding.

<div id="toc">
</div> 

## Eight Atoms

Values of these types are immutable:

- `Null`, `Str Int Float` - data types
- `Range` - iteration over `3 .. 5`
- `Eggex Match` - pattern matching

A type with one value:

- `Stdin` - used for buffered line I/O in the YSH `for` loop

<!--
It seems like stdin could be a file descriptor, but that doesn't fit with the
shell I/O model.  You always REDIRECT first, then read from stdin.  And you
don't read incrementally from multiple files at once.
-->

The `Str` type is the only type shared between OSH and YSH.

<!--

These are variants of VALIDATED strings, with lazily materialized views?

- value.{Htm8,Tsv8,Json8} ?

-->

## Five Mutable Types

YSH containers:

- `List Dict` - arbitrarily recursive

A special YSH type for "out params":

- `Place` - created by `&myvar`, and mutated by `call place->setValue(42)`

Containers for bash compatibility in OSH:

- `BashArray BashAssoc` - flat

## `Obj` is for User-defined Types

- `Obj` - has a prototype chain

Objects allow **polymorphism**.  See [YSH Objects](objects.html).

Modules and types are represented by `Obj` instances of a certain shape, not by
primitive types.

1. Modules are `Obj` with attributes, and an `__invoke__` method.
1. Types are `Obj` with a `__str__` method, and are often compared for
   identity.

In general, Objects are mutable.  Do not mutate modules or types!

## Five Units of Code

Values of these types are immutable:

- `BoundFunc` (for methods)
- `BuiltinFunc Func`
- `BuiltinProc Proc`

## Five Types for Reflection

Values of these types are immutable:

- `CommandFrag Command`, `ExprFrag Expr` (TODO)

A handle to a stack frame:

- `Frame` - implicitly mutable, by `setvar`, etc.

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



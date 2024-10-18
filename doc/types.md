---
default_highlighter: oils-sh
---

Types in the Oils Runtime - OSH and YSH
===========

This doc lists the type of values in the Oils runtime.

<div id="toc">
</div> 

## Seven Atoms

These types are immutable:

- `Null Str Int Float`
- `Range`
- `Eggex Match`

Of these types, OSH only uses `Str`.  That is, the string type is the only type
shared between OSH and YSH.

## Four Mutable Containers

For YSH:

- `List Dict`

For bash compatibility in OSH:

- `BashArray BashAssoc`

## `Obj` is for User-defined Types

- `Obj` 

Objects allow **polymorphism**.  See [YSH Objects](objects.html).

## Five Units of Code

- `BoundFunc` (for methods)
- `BuiltinFunc Func`
- `BuiltinProc Proc`

(These types are immutable)

## Six Types for Reflection

- `CommandFrag Command`, `ExprFrag Expr` (TODO)
- `Place Frame`

(These types are immutable)

## Appendix

### The JSON Data Model

These types can be serialized to and from JSON:

- `Null Str Int Float List Dict`

### Implementation Details

These types used internally:

- `value.Undef` - used when looking up a variable
- `value.Interrupted` - for SIGINT
- `value.Slice` - for a[1:2]

### Related

- [Types and Methods](ref/chap-type-method.html) in the [Oils
  Reference](ref/index.html)


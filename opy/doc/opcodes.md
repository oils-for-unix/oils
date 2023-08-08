Notes on VM Opcodes
===================

2018 Bytecode assessement
-------------------------

### Same

Stack Management Bytecodes that are the same:

- `POP_TOP`
- `DUP_TOP_TWO`
- `ROT_{TWO,THREE,FOUR}`

(We could switch to a register VM, but that would be an completely orthogonal
change.)

Control Flow Bytecodes that are the same:

- `SETUP_LOOP`
- `SETUP_WITH`
  - `WITH_CLEANUP`
- `SETUP_{EXCEPT,FINALLY}`
  - `END_FINALLY`
- `POP_BLOCK`
- `JUMP_{FORWARD,ABSOLUTE,...}`
- `POP_JUMP_*`
- `{BREAK,CONTINUE}_LOOP`
- `RETURN_VALUE`
- `RAISE_VARARGS` -- although it's not as general
- `GET_ITER`

Data structure bytecodes that are likely the same:

- `{LIST,SET,MAP}_ADD`
- `STORE_MAP`
- `BUILD_{TUPLE,LIST,SET,MAP}`
- `SLICE_*`

At least in the beginning they are the same.  Later we might have specialized
data structures, e.g. `Array<Str>`, which is extremely common in shell.

### Changed

Load / Store bytescodes that will take indices instead of names:

- `{LOAD,STORE}_NAME`
  - fast variants go away: `{LOAD,STORE}_FAST`
- `{LOAD,STORE}_GLOBAL`
- `{LOAD,STORE}_ATTR` - for object members


Highly Changed based on language semantics

- `CALL_FUNCTION_*` -- Instead of four variants, we may just have one more
  static kind.
  - It will support `f(msg, *args)` and `f(*args, **kwargs)`, but maybe not
    much else?

Bytecodes that can be type-specialized:

- `BINARY_*`
- `UNARY_*`
- `COMPARE_OP` -- or maybe just don't allow nonsensical comparisons

Maybe type-specialized:

- `FOR_ITER` -- iterating items in a list, iterating characters in a string
  could be compiled statically.  In other words, the iterator protocol isn't
  quite necessary.

### Removed

Dynamic bytecodes that will go away, because names are statically resolved:

- `BUILD_CLASS`
- `MAKE_FUNCTION`
- `IMPORT_{NAME,STAR}`
- maybe: `MAKE_CLOSURE`: this should be done statically?  Closures and classes
  should be the same?  It's like calling a constructor.

Other Removed:

- `DELETE_NAME`: Namespaces are static
- Might be unnecessary for our purposes: `YIELD_FROM`
- `EXEC_STMT`: I want a different interface to the compiler, for
  metaprogramming purposes.

Deprecated:

- `PRINT_*` -- this should just be a normal function call

### Additions

- Bytecodes for ASDL structures?
- Bytecodes for shell?
- For parsing VM?

2017
----

This is an elaboration on:

https://docs.python.org/2/library/dis.html

I copy the descriptions and add my notes, based on what I'm working on.



`SETUP_LOOP(delta)`

Pushes a block for a loop onto the block stack. The block spans from the
current instruction with a size of delta bytes.

NOTES: compiler2 generates an extra SETUP_LOOP, for generator expressions,
along with POP_BLOCK.


`POP_BLOCK()`

Removes one block from the block stack. Per frame, there is a stack of blocks,
denoting nested loops, try statements, and such.


`LOAD_CLOSURE(i)`

Pushes a reference to the cell contained in slot `i` of the cell and free
variable storage. The name of the variable is `co_cellvars[i]` if i is less
than the length of `co_cellvars`. Otherwise it is
`co_freevars[i - len(co_cellvars)]`.

NOTES: compiler2 generates an extra one of these


`MAKE_CLOSURE(argc)`

Creates a new function object, sets its `func_closure` slot, and pushes it on
the stack. `TOS` is the code associated with the function, `TOS1` the tuple
containing cells for the closure’s free variables. The function also has `argc`
default parameters, which are found below the cells.


`LOAD_DEREF(i)`

Loads the cell contained in slot `i` of the cell and free variable storage.
Pushes a reference to the object the cell contains on the stack.


`GET_ITER()`

Implements TOS = iter(TOS).

NOTES: Hm how do I implement this?  It turns it from a collection into an
iterator.  Gah.

    PyObject *iter = PyObject_GetIter(iterable); 

    objects/abstract.c - 
    objects/iterobject.c - PySeqIter_New
    PySeqIter_Type has a it_seq field.  The PyObject being iterated over.  It
    maintains an index too.
    How does items() work as an iterable then?

    Then iter_iternext() calls:
    PySequence_GetItem(seq, it->it_index)



`LOAD_FAST(var_num)`

Pushes a reference to the local `co_varnames[var_num]` onto the stack.

NOTES:
This still does a named lookup?  Generator expressions do `LOAD_FAST 0 (.0)`
since there is no formal parameter name.

Oh I see, there is a `PyObject** fastlocals` in EvalFrame

It's initialized to `f->f_localsplus` -- frame holds them.  Oh I see, that's
where the frame setup is different!  Don't need inspect.callargs.


FastCall populates fastlocals from `PyObject** args` and `nargs`.








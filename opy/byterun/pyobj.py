"""Implementations of Python fundamental objects for Byterun."""
from __future__ import print_function

import collections
import dis
import inspect
import sys
import types


def make_cell(value):
    # Thanks to Alex Gaynor for help with this bit of twistiness.
    # Construct an actual cell object by creating a closure right here,
    # and grabbing the cell object out of the function we create.
    fn = (lambda x: lambda: x)(value)
    return fn.func_closure[0]


class Function(object):
    __slots__ = [
        'func_code', 'func_name', 'func_defaults', 'func_globals',
        'func_locals', 'func_dict', 'func_closure',
        '__name__', '__dict__', '__doc__',
        '_vm', '_func',
    ]

    def __init__(self, name, code, globs, locs, defaults, closure, vm):
        self._vm = vm
        self.func_code = code
        self.func_name = self.__name__ = name or code.co_name
        self.func_defaults = tuple(defaults)
        self.func_globals = globs
        self.func_locals = locs
        self.__dict__ = {}
        self.func_closure = closure
        self.__doc__ = code.co_consts[0] if code.co_consts else None

        # Sometimes, we need a real Python function.  This is for that.
        # For some reason types.FunctionType doesn't accept normal keyword
        # args?  Like args=, closure= ?
        # Is this only used for inspect.getcallargs?

        kw = {'argdefs': self.func_defaults}
        if closure:
            kw['closure'] = tuple(make_cell(0) for _ in closure)
        self._func = types.FunctionType(code, globs, **kw)

    def __repr__(self):         # pragma: no cover
        return '<byterun Function %s at 0x%08x>' % (
            self.func_name, id(self)
        )

    def __get__(self, instance, owner):
        if instance is not None:
            return Method(instance, owner, self)
        return Method(None, owner, self)

    def __call__(self, *args, **kwargs):
        #if PY2 and self.func_name in ["<setcomp>", "<dictcomp>", "<genexpr>"]:
            # D'oh! http://bugs.python.org/issue19611 Py2 doesn't know how to
            # inspect set comprehensions, dict comprehensions, or generator
            # expressions properly.  They are always functions of one argument,
            # so just do the right thing.
            #assert len(args) == 1 and not kwargs, "Surprising comprehension!"
            #callargs = {".0": args[0]}

        # Different workaround for issue 19611 that works with
        # compiler2-generated code.  Note that byterun does not use fastlocals,
        # so the name matters.  With fastlocals, the co_varnames entry is just
        # a comment; the index is used instead.
        code = self.func_code
        if code.co_argcount == 1 and code.co_varnames[0] == '.0':
            callargs = {".0": args[0]}
        else:
            # NOTE: Can get ValueError due to issue 19611
            callargs = inspect.getcallargs(self._func, *args, **kwargs)
        #print('-- func_name %s CALLS ARGS %s' % (self.func_name, callargs))

        frame = self._vm.make_frame(self.func_code, callargs,
                                    self.func_globals, {})

        CO_GENERATOR = 32           # flag for "this code uses yield"
        if self.func_code.co_flags & CO_GENERATOR:
            gen = Generator(frame, self._vm)
            frame.generator = gen
            retval = gen
        else:
            retval = self._vm.run_frame(frame)
        return retval

class Method(object):
    def __init__(self, obj, _class, func):
        self.im_self = obj
        self.im_class = _class
        self.im_func = func

    def __repr__(self):         # pragma: no cover
        name = "%s.%s" % (self.im_class.__name__, self.im_func.func_name)
        if self.im_self is not None:
            return '<Bound Method %s of %s>' % (name, self.im_self)
        else:
            return '<Unbound Method %s>' % (name,)

    def __call__(self, *args, **kwargs):
        if self.im_self is not None:
            return self.im_func(self.im_self, *args, **kwargs)
        else:
            return self.im_func(*args, **kwargs)


class Cell(object):
    """A fake cell for closures.

    Closures keep names in scope by storing them not in a frame, but in a
    separate object called a cell.  Frames share references to cells, and
    the LOAD_DEREF and STORE_DEREF opcodes get and set the value from cells.

    This class acts as a cell, though it has to jump through two hoops to make
    the simulation complete:

        1. In order to create actual FunctionType functions, we have to have
           actual cell objects, which are difficult to make. See the twisty
           double-lambda in __init__.

        2. Actual cell objects can't be modified, so to implement STORE_DEREF,
           we store a one-element list in our cell, and then use [0] as the
           actual value.

    """
    def __init__(self, value):
        self.contents = value

    def get(self):
        return self.contents

    def set(self, value):
        self.contents = value


# PyTryBlock in CPython, for SETUP_EXCEPT, etc.
Block = collections.namedtuple("Block", "type, handler, level")


class Frame(object):
    def __init__(self, f_code, f_globals, f_locals, f_back):
        self.f_code = f_code
        self.f_globals = f_globals
        self.f_locals = f_locals
        self.f_back = f_back
        self.stack = []
        if f_back:
            self.f_builtins = f_back.f_builtins
        else:
            self.f_builtins = f_locals['__builtins__']
            if hasattr(self.f_builtins, '__dict__'):
                self.f_builtins = self.f_builtins.__dict__

        self.f_lineno = f_code.co_firstlineno
        self.f_lasti = 0

        if f_code.co_cellvars:
            self.cells = {}
            if not f_back.cells:
                f_back.cells = {}
            for var in f_code.co_cellvars:
                # Make a cell for the variable in our locals, or None.
                cell = Cell(self.f_locals.get(var))
                f_back.cells[var] = self.cells[var] = cell
        else:
            self.cells = None

        if f_code.co_freevars:
            if not self.cells:
                self.cells = {}
            for var in f_code.co_freevars:
                assert self.cells is not None
                assert f_back.cells, "f_back.cells: %r" % (f_back.cells,)
                self.cells[var] = f_back.cells[var]

        self.block_stack = []
        self.generator = None

    def __repr__(self):         # pragma: no cover
        return '<Frame at 0x%08x: %r @ %d>' % (
            id(self), self.f_code.co_filename, self.f_lineno
        )

    def top(self):
        """Return the value at the top of the stack, with no changes."""
        return self.stack[-1]

    def pop(self, i=0):
        """Pop a value from the stack.

        Default to the top of the stack, but `i` can be a count from the top
        instead.

        """
        return self.stack.pop(-1-i)

    def push(self, *vals):
        """Push values onto the value stack."""
        self.stack.extend(vals)

    def popn(self, n):
        """Pop a number of values from the value stack.

        A list of `n` values is returned, the deepest value first.
        """
        if n:
            ret = self.stack[-n:]
            del self.stack[-n:]
            return ret
        else:
            return []

    def peek(self, n):
        """Get a value `n` entries down in the stack, without changing the stack."""
        return self.stack[-n]

    def jump(self, offset):
        """Move the bytecode pointer to `offset`, so it will execute next."""
        self.f_lasti = offset

    def push_block(self, type, handler=None, level=None):
        """Used for SETUP_{LOOP,EXCEPT,FINALLY,WITH}."""
        if level is None:
            level = len(self.stack)
        self.block_stack.append(Block(type, handler, level))

    def pop_block(self):
        return self.block_stack.pop()

    def _unwind_block(self, block, vm):
        """
        Args:
          vm: VirtualMachineError to possibly mutate
        """
        if block.type == 'except-handler':
            offset = 3
        else:
            offset = 0

        while len(self.stack) > block.level + offset:
            self.pop()

        if block.type == 'except-handler':
            tb, value, exctype = self.popn(3)
            vm.last_exception = exctype, value, tb

    def handle_block_stack(self, why, vm):
        """
        After every bytecode that returns why != None, handle everything on the
        block stack.

        The block stack and data stack are shuffled for looping, exception
        handling, or returning.
        """
        assert why != 'yield'

        block = self.block_stack[-1]
        if block.type == 'loop' and why == 'continue':
            self.jump(vm.return_value)
            why = None
            return why

        self.pop_block()
        self._unwind_block(block, vm)

        if block.type == 'loop' and why == 'break':
            why = None
            self.jump(block.handler)
            return why

        if (block.type in ('finally', 'with') or
            block.type == 'setup-except' and why == 'exception'):
            if why == 'exception':
                exctype, value, tb = vm.last_exception
                self.push(tb, value, exctype)
            else:
                if why in ('return', 'continue'):
                    self.push(vm.return_value)
                self.push(why)

            why = None
            self.jump(block.handler)
            return why

        return why

    def decode_next(self):
        """
        Parse 1 - 3 bytes of bytecode into an instruction and maybe arguments.
        """
        byteCode = ord(self.f_code.co_code[self.f_lasti])
        self.f_lasti += 1

        arguments = []
        if byteCode >= dis.HAVE_ARGUMENT:
            arg = self.f_code.co_code[self.f_lasti : self.f_lasti+2]
            self.f_lasti += 2
            intArg = ord(arg[0]) + (ord(arg[1]) << 8)
            if byteCode in dis.hasconst:
                arg = self.f_code.co_consts[intArg]
            elif byteCode in dis.hasfree:
                if intArg < len(self.f_code.co_cellvars):
                    arg = self.f_code.co_cellvars[intArg]
                else:
                    var_idx = intArg - len(self.f_code.co_cellvars)
                    arg = self.f_code.co_freevars[var_idx]
            elif byteCode in dis.hasname:
                arg = self.f_code.co_names[intArg]
            elif byteCode in dis.hasjrel:
                arg = self.f_lasti + intArg
            elif byteCode in dis.hasjabs:
                arg = intArg
            elif byteCode in dis.haslocal:
                arg = self.f_code.co_varnames[intArg]
            else:
                arg = intArg
            arguments = [arg]

        byteName = dis.opname[byteCode]
        return byteName, arguments

    def line_number(self):
        """Get the current line number the frame is executing."""
        # We don't keep f_lineno up to date, so calculate it based on the
        # instruction address and the line number table.
        lnotab = self.f_code.co_lnotab
        byte_increments = lnotab[0::2]
        line_increments = lnotab[1::2]

        byte_num = 0
        line_num = self.f_code.co_firstlineno

        for byte_incr, line_incr in zip(byte_increments, line_increments):
            byte_incr = ord(byte_incr)
            line_incr = ord(line_incr)

            byte_num += byte_incr
            if byte_num > self.f_lasti:
                break
            line_num += line_incr

        return line_num


class Generator(object):
    def __init__(self, g_frame, vm):
        self.g_frame = g_frame
        self._vm = vm
        self.started = False
        self.finished = False

    # Part of the iterator protocol.
    def __iter__(self):
        """DO_NOT_INTERPRET"""
        return self

    # Part of the iterator protocol.
    def next(self):
        """DO_NOT_INTERPRET"""
        # Docstring is a hack for pyvm2 !  Is there a better way?
        # This is a THIRD path for a function.

        return self.send(None)

    # Part of the iterator protocol.
    def send(self, value=None):
        """DO_NOT_INTERPRET"""
        if not self.started and value is not None:
            raise TypeError("Can't send non-None value to a just-started generator")
        self.g_frame.stack.append(value)
        self.started = True
        val = self._vm.resume_frame(self.g_frame)
        if self.finished:
            raise StopIteration(val)
        return val

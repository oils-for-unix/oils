"""A pure-Python Python bytecode interpreter."""
# Based on:
# pyvm2 by Paul Swartz (z3p), from http://www.twistedmatrix.com/users/z3p/

from __future__ import print_function, division
import linecache
import operator
import os
import repr as repr_lib  # Don't conflict with builtin repr()
import sys
import traceback
import types

# Function used in MAKE_FUNCTION, MAKE_CLOSURE
# Generator used in YIELD_FROM, which we might not need.
from pyobj import Frame, Block, Function, Generator

from opy.lib import dis

# Create a repr that won't overflow.
repr_obj = repr_lib.Repr()
repr_obj.maxother = 120
repper = repr_obj.repr

VERBOSE = True
VERBOSE = False

# Different than log
def debug(msg, *args):
  if not VERBOSE:
    return

  debug1(msg, *args)


def debug1(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


class VirtualMachineError(Exception):
    """For raising errors in the operation of the VM."""
    pass


class GuestException(Exception):
    """For errors raised by the interpreter program.

    NOTE: I added this because the host traceback was conflated with the guest
    traceback.
    """

    def __init__(self, exctype, value, frames):
        self.exctype = exctype
        if isinstance(value, GuestException):
          raise AssertionError
        self.value = value
        self.frames = frames

    def __str__(self):
        parts = []
        parts.append('Guest Exception Traceback:')
        parts.append('')
        for f in self.frames:
            filename = f.f_code.co_filename
            lineno = f.line_number()
            parts.append(
                '- File "%s", line %d, in %s' %
                (filename, lineno, f.f_code.co_name))
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
            if line:
                parts.append('    ' + line.strip())
        parts.append('')
        parts.append('exctype: %s' % self.exctype)
        parts.append('value: %s' % self.value)

        return '\n'.join(parts) + '\n'


def run_code(vm, code, f_globals=None):
    """Main entry point.

    Used by tests and by execfile.
    """
    frame = vm.make_frame(code, f_globals=f_globals)
    val = vm.run_frame(frame)
    vm.check_invariants()
    if os.getenv('BYTERUN_SUMMARY'):
      debug1('*** Byterun executed for %d ticks', vm.num_ticks)
    # If we return the number of ticks here, the unit tests break.
    return val


class VirtualMachine(object):

    def __init__(self, subset=False, verbose=VERBOSE):
        """
        Args:
          subset: turn off bytecodes that OPy doesn't need (e.g. print
            statement, etc.)
          verbose: turn on logging
        """
        self.subset = subset
        self.more_info = False
        #self.more_info = True
        self.verbose = verbose
        # some objects define __repr__, which means our debug() logging screws
        # things up!  Even though they don't have side effects, this somehow
        # matters.
        self.repr_ok = True

        # The call stack of frames.
        self.frames = []
        # The current frame.
        self.frame = None
        self.return_value = None

        self.last_exception = None
        self.except_frames = []  # Frames saved for GuestException
        self.cur_line = None  # current line number
        self.num_ticks = 0

    def top(self):
        return self.frame.top()

    def pop(self, i=0):
        return self.frame.pop(i=i)

    def push(self, *vals):
        self.frame.push(*vals)

    def popn(self, n):
        return self.frame.popn(n)

    def peek(self, n):
        return self.frame.peek(n)

    def jump(self, offset):
        self.frame.jump(offset)

    def make_frame(self, code, callargs={}, f_globals=None, f_locals=None):
        """
        Called by self.run_code and Function.__call__.
        """
        # NOTE: repper causes problems running code!  See testdata/repr_method.py
        #debug("make_frame: code=%r, callargs=%s", code, repper(callargs))
        if f_globals is not None:
            f_globals = f_globals
            if f_locals is None:
                f_locals = f_globals
        elif self.frames:
            f_globals = self.frame.f_globals
            f_locals = {}
        else:
            f_globals = f_locals = {
                '__builtins__': __builtins__,
                '__name__': '__main__',
                '__doc__': None,
                '__package__': None,
            }
        f_locals.update(callargs)
        frame = Frame(code, f_globals, f_locals, self.frame)
        return frame

    def resume_frame(self, frame):
        """Called by Generator."""
        frame.f_back = self.frame

        # NOTE: Could raise exceptions!
        val = self.run_frame(frame)

        frame.f_back = None
        return val

    def log_tick(self, byteName, arguments, opoffset, linestarts):
        """ Log arguments, block stack, and data stack for each opcode."""
        indent = "    " * (len(self.frames)-1)
        stack_rep = repper(self.frame.stack)
        #block_stack_rep = repper(self.frame.block_stack)
        # repr_lib is causing problems
        if self.repr_ok:
            stack_rep = repr(self.frame.stack)
            #block_stack_rep = repr(self.frame.block_stack)

        arg_str = ''
        if arguments and self.repr_ok:
            arg_str = ' %r' % (arguments[0],)

        # TODO: Should increment

        li = linestarts.get(opoffset, None)
        if li is not None and self.cur_line != li:
          self.cur_line = li

        debug('%s%d: %s%s (line %s)', indent, opoffset, byteName, arg_str,
              self.cur_line)
        if self.repr_ok:
            debug('  %sval stack: %s', indent, stack_rep)
        #debug('  %sblock stack: %s', indent, block_stack_rep)
        debug('')

    def dispatch(self, byteName, arguments):
        """ Dispatch by bytename to the corresponding methods.
        Exceptions are caught and set on the virtual machine."""
        why = None
        try:
            if byteName.startswith('UNARY_'):
                self.unaryOperator(byteName[6:])
            elif byteName.startswith('BINARY_'):
                self.binaryOperator(byteName[7:])
            elif byteName.startswith('INPLACE_'):
                self.inplaceOperator(byteName[8:])
            elif 'SLICE+' in byteName:
                self.sliceOperator(byteName)
            else:
                # dispatch
                bytecode_fn = getattr(self, 'byte_%s' % byteName, None)
                if not bytecode_fn:            # pragma: no cover
                    raise VirtualMachineError(
                        "unknown bytecode type: %s" % byteName
                    )
                why = bytecode_fn(*arguments)

        except:
            # Deal with exceptions encountered while executing the op.
            self.last_exception = sys.exc_info()[:2] + (None,)

            # NOTE: Why doesn't byterun use this info?
            #tb = sys.exc_info()[2]
            #traceback.print_tb(tb)

            #debug1("Caught exception during execution of %s: %d", byteName,
            #       len(self.frames))
            why = 'exception'
            self.except_frames = list(self.frames)

        return why

    # Helpers for run_frame
    def _push_frame(self, frame):
        self.frames.append(frame)
        self.frame = frame

    def _pop_frame(self):
        self.frames.pop()
        if self.frames:
            self.frame = self.frames[-1]
        else:
            self.frame = None

    def run_frame(self, frame):
        """Run a frame until it returns or raises an exception.

        This function raises GuestException or returns the return value.

        Corresponds to PyEval_EvalFrameEx in ceval.c.  That returns 'PyObject*
        retval' -- but how does it indicate an exception?

        I think retval is NULL, and then

        """
        # bytecode offset -> line number
        #print('frame %s ' % frame)
        # NOTE: Also done in Frmae.line_number()
        linestarts = dict(dis.findlinestarts(frame.f_code))
        #print('STARTS %s ' % linestarts)

        self._push_frame(frame)
        while True:
            self.num_ticks += 1

            opoffset = self.frame.f_lasti  # For logging only
            byteName, arguments = self.frame.decode_next()
            if self.verbose:
                self.log_tick(byteName, arguments, opoffset, linestarts)

            # When unwinding the block stack, we need to keep track of why we
            # are doing it.

            # NOTE: In addition to returning why == 'exception', this can also
            # RAISE GuestException from recursive call via call_function.

            why = self.dispatch(byteName, arguments)
            if why == 'exception':
                # TODO: ceval calls PyTraceBack_Here, not sure what that does.
                pass

            if why == 'reraise':
                why = 'exception'

            if why != 'yield':

                # NOTE: why is used in a frame INTERNALLY after bytecode dispatch.
                # But what about ACROSS frames.  We need to unwind the call
                # stack too!  How is that done?
                # I don't want it to be done with GuestException!

                while why and frame.block_stack:
                    debug('WHY %s', why)
                    debug('STACK %s', frame.block_stack)
                    why = self.frame.handle_block_stack(why, self)

            if why:
                break

        # TODO: handle generator exception state

        self._pop_frame()

        if why == 'exception':
            exctype, value, tb = self.last_exception

            #debug('exctype: %s' % exctype)
            #debug('value: %s' % value)
            #debug('unused tb: %s' % tb)

            if self.more_info:
                # Recursive function calls can cause this I guess.
                if isinstance(value, GuestException):
                    raise value
                else:
                    # Raise an exception with the EMULATED (guest) stack frames.
                    raise GuestException(exctype, value, self.except_frames)
            else:
                raise exctype, value, tb

        #debug1('num_ticks: %d' % num_ticks)
        return self.return_value

    def check_invariants(self):
      # Check some invariants
      if self.frames:            # pragma: no cover
          raise VirtualMachineError("Frames left over!")
      if self.frame and self.frame.stack:             # pragma: no cover
          raise VirtualMachineError("Data left on stack! %r" % self.frame.stack)

    ## Stack manipulation

    def byte_LOAD_CONST(self, const):
        self.push(const)

    def byte_POP_TOP(self):
        self.pop()

    def byte_DUP_TOP(self):
        self.push(self.top())

    def byte_DUP_TOPX(self, count):
        items = self.popn(count)
        for i in [1, 2]:
            self.push(*items)

    def byte_DUP_TOP_TWO(self):
        # Py3 only
        a, b = self.popn(2)
        self.push(a, b, a, b)

    def byte_ROT_TWO(self):
        a, b = self.popn(2)
        self.push(b, a)

    def byte_ROT_THREE(self):
        a, b, c = self.popn(3)
        self.push(c, a, b)

    def byte_ROT_FOUR(self):
        a, b, c, d = self.popn(4)
        self.push(d, a, b, c)

    ## Names

    def byte_LOAD_NAME(self, name):
        frame = self.frame
        if name in frame.f_locals:
            val = frame.f_locals[name]
        elif name in frame.f_globals:
            val = frame.f_globals[name]
        elif name in frame.f_builtins:
            val = frame.f_builtins[name]
        else:
            raise NameError("name '%s' is not defined" % name)
        self.push(val)

    def byte_STORE_NAME(self, name):
        self.frame.f_locals[name] = self.pop()

    def byte_DELETE_NAME(self, name):
        del self.frame.f_locals[name]

    def byte_LOAD_FAST(self, name):
        if name in self.frame.f_locals:
            val = self.frame.f_locals[name]
        else:
            raise UnboundLocalError(
                "local variable '%s' referenced before assignment" % name
            )
        self.push(val)

    def byte_STORE_FAST(self, name):
        self.frame.f_locals[name] = self.pop()

    def byte_DELETE_FAST(self, name):
        del self.frame.f_locals[name]

    def byte_LOAD_GLOBAL(self, name):
        f = self.frame
        if name in f.f_globals:
            val = f.f_globals[name]
        elif name in f.f_builtins:
            val = f.f_builtins[name]
        else:
            raise NameError("global name '%s' is not defined" % name)
        self.push(val)

    def byte_STORE_GLOBAL(self, name):
        f = self.frame
        f.f_globals[name] = self.pop()

    def byte_LOAD_DEREF(self, name):
        self.push(self.frame.cells[name].get())

    def byte_STORE_DEREF(self, name):
        self.frame.cells[name].set(self.pop())

    def byte_LOAD_LOCALS(self):
        self.push(self.frame.f_locals)

    ## Operators

    UNARY_OPERATORS = {
        'POSITIVE': operator.pos,
        'NEGATIVE': operator.neg,
        'NOT':      operator.not_,
        'CONVERT':  repr,
        'INVERT':   operator.invert,
    }

    def unaryOperator(self, op):
        x = self.pop()
        self.push(self.UNARY_OPERATORS[op](x))

    BINARY_OPERATORS = {
        'POWER':    pow,
        'MULTIPLY': operator.mul,
        'DIVIDE':   getattr(operator, 'div', lambda x, y: None),
        'FLOOR_DIVIDE': operator.floordiv,
        'TRUE_DIVIDE':  operator.truediv,
        'MODULO':   operator.mod,
        'ADD':      operator.add,
        'SUBTRACT': operator.sub,
        'SUBSCR':   operator.getitem,
        'LSHIFT':   operator.lshift,
        'RSHIFT':   operator.rshift,
        'AND':      operator.and_,
        'XOR':      operator.xor,
        'OR':       operator.or_,
    }

    def binaryOperator(self, op):
        x, y = self.popn(2)
        self.push(self.BINARY_OPERATORS[op](x, y))

    def inplaceOperator(self, op):
        x, y = self.popn(2)
        if op == 'POWER':
            x **= y
        elif op == 'MULTIPLY':
            x *= y
        elif op in ['DIVIDE', 'FLOOR_DIVIDE']:
            x //= y
        elif op == 'TRUE_DIVIDE':
            x /= y
        elif op == 'MODULO':
            x %= y
        elif op == 'ADD':
            x += y
        elif op == 'SUBTRACT':
            x -= y
        elif op == 'LSHIFT':
            x <<= y
        elif op == 'RSHIFT':
            x >>= y
        elif op == 'AND':
            x &= y
        elif op == 'XOR':
            x ^= y
        elif op == 'OR':
            x |= y
        else:           # pragma: no cover
            raise VirtualMachineError("Unknown in-place operator: %r" % op)
        self.push(x)

    def sliceOperator(self, op):
        start = 0
        end = None          # we will take this to mean end
        op, count = op[:-2], int(op[-1])
        if count == 1:
            start = self.pop()
        elif count == 2:
            end = self.pop()
        elif count == 3:
            end = self.pop()
            start = self.pop()
        l = self.pop()
        if end is None:
            end = len(l)
        if op.startswith('STORE_'):
            l[start:end] = self.pop()
        elif op.startswith('DELETE_'):
            del l[start:end]
        else:
            self.push(l[start:end])

    COMPARE_OPERATORS = [
        operator.lt,
        operator.le,
        operator.eq,
        operator.ne,
        operator.gt,
        operator.ge,
        lambda x, y: x in y,
        lambda x, y: x not in y,
        lambda x, y: x is y,
        lambda x, y: x is not y,
        lambda x, y: issubclass(x, Exception) and issubclass(x, y),
    ]

    def byte_COMPARE_OP(self, opnum):
        x, y = self.popn(2)
        self.push(self.COMPARE_OPERATORS[opnum](x, y))

    ## Attributes and indexing

    def byte_LOAD_ATTR(self, attr):
        obj = self.pop()
        #debug1('obj=%s, attr=%s', obj, attr)
        #debug1('dir(obj)=%s', dir(obj))
        val = getattr(obj, attr)
        self.push(val)

    def byte_STORE_ATTR(self, name):
        val, obj = self.popn(2)
        setattr(obj, name, val)

    def byte_DELETE_ATTR(self, name):
        obj = self.pop()
        delattr(obj, name)

    def byte_STORE_SUBSCR(self):
        val, obj, subscr = self.popn(3)
        obj[subscr] = val

    def byte_DELETE_SUBSCR(self):
        obj, subscr = self.popn(2)
        del obj[subscr]

    ## Building

    def byte_BUILD_TUPLE(self, count):
        elts = self.popn(count)
        self.push(tuple(elts))

    def byte_BUILD_LIST(self, count):
        elts = self.popn(count)
        self.push(elts)

    def byte_BUILD_SET(self, count):
        # TODO: Not documented in Py2 docs.
        elts = self.popn(count)
        self.push(set(elts))

    def byte_BUILD_MAP(self, size):
        # size is ignored.
        self.push({})

    def byte_STORE_MAP(self):
        the_map, val, key = self.popn(3)
        the_map[key] = val
        self.push(the_map)

    def byte_UNPACK_SEQUENCE(self, count):
        seq = self.pop()
        for x in reversed(seq):
            self.push(x)

    def byte_BUILD_SLICE(self, count):
        if count == 2:
            x, y = self.popn(2)
            self.push(slice(x, y))
        elif count == 3:
            x, y, z = self.popn(3)
            self.push(slice(x, y, z))
        else:           # pragma: no cover
            raise VirtualMachineError("Strange BUILD_SLICE count: %r" % count)

    def byte_LIST_APPEND(self, count):
        val = self.pop()
        the_list = self.peek(count)
        the_list.append(val)

    def byte_SET_ADD(self, count):
        val = self.pop()
        the_set = self.peek(count)
        the_set.add(val)

    def byte_MAP_ADD(self, count):
        val, key = self.popn(2)
        the_map = self.peek(count)
        the_map[key] = val

    ## Printing

    if 0:   # Only used in the interactive interpreter, not in modules.
        def byte_PRINT_EXPR(self):
            print(self.pop())

    def byte_PRINT_ITEM(self):
        item = self.pop()
        self.print_item(item)

    def byte_PRINT_ITEM_TO(self):
        to = self.pop()
        item = self.pop()
        self.print_item(item, to)

    def byte_PRINT_NEWLINE(self):
        self.print_newline()

    def byte_PRINT_NEWLINE_TO(self):
        to = self.pop()
        self.print_newline(to)

    def print_item(self, item, to=None):
        if to is None:
            to = sys.stdout
        if to.softspace:
            print(" ", end="", file=to)
            to.softspace = 0
        print(item, end="", file=to)
        if isinstance(item, str):
            if (not item) or (not item[-1].isspace()) or (item[-1] == " "):
                to.softspace = 1
        else:
            to.softspace = 1

    def print_newline(self, to=None):
        if to is None:
            to = sys.stdout
        print("", file=to)
        to.softspace = 0

    ## Jumps

    def byte_JUMP_FORWARD(self, jump):
        self.jump(jump)

    def byte_JUMP_ABSOLUTE(self, jump):
        self.jump(jump)

    if 0:   # Not in py2.7
        def byte_JUMP_IF_TRUE(self, jump):
            val = self.top()
            if val:
                self.jump(jump)

        def byte_JUMP_IF_FALSE(self, jump):
            val = self.top()
            if not val:
                self.jump(jump)

    def byte_POP_JUMP_IF_TRUE(self, jump):
        val = self.pop()
        if val:
            self.jump(jump)

    def byte_POP_JUMP_IF_FALSE(self, jump):
        val = self.pop()
        if not val:
            self.jump(jump)

    def byte_JUMP_IF_TRUE_OR_POP(self, jump):
        val = self.top()
        if val:
            self.jump(jump)
        else:
            self.pop()

    def byte_JUMP_IF_FALSE_OR_POP(self, jump):
        val = self.top()
        if not val:
            self.jump(jump)
        else:
            self.pop()

    ## Blocks

    def byte_SETUP_LOOP(self, dest):
        self.frame.push_block('loop', dest)

    def byte_GET_ITER(self):
        self.push(iter(self.pop()))

    def byte_FOR_ITER(self, jump):
        iterobj = self.top()
        try:
            v = next(iterobj)
            self.push(v)
        except StopIteration:
            self.pop()
            self.jump(jump)

    def byte_BREAK_LOOP(self):
        return 'break'

    def byte_CONTINUE_LOOP(self, dest):
        # This is a trick with the return value.
        # While unrolling blocks, continue and return both have to preserve
        # state as the finally blocks are executed.  For continue, it's
        # where to jump to, for return, it's the value to return.  It gets
        # pushed on the stack for both, so continue puts the jump destination
        # into return_value.
        self.return_value = dest
        return 'continue'

    def byte_SETUP_EXCEPT(self, dest):
        self.frame.push_block('setup-except', dest)

    def byte_SETUP_FINALLY(self, dest):
        self.frame.push_block('finally', dest)

    def byte_END_FINALLY(self):
        v = self.pop()
        #debug('V %s', v)
        if isinstance(v, str):
            why = v
            if why in ('return', 'continue'):
                self.return_value = self.pop()
        elif v is None:
            why = None
        elif issubclass(v, BaseException):
            exctype = v
            val = self.pop()
            tb = self.pop()
            self.last_exception = (exctype, val, tb)

            why = 'reraise'
        else:       # pragma: no cover
            raise VirtualMachineError("Confused END_FINALLY")
        return why

    def byte_POP_BLOCK(self):
        self.frame.pop_block()

    def byte_RAISE_VARARGS(self, argc):
        # NOTE: the dis docs are completely wrong about the order of the
        # operands on the stack!
        exctype = val = tb = None
        if argc == 0:
            exctype, val, tb = self.last_exception
        elif argc == 1:
            exctype = self.pop()
        elif argc == 2:
            val = self.pop()
            exctype = self.pop()
        elif argc == 3:
            tb = self.pop()
            val = self.pop()
            exctype = self.pop()

        # There are a number of forms of "raise", normalize them somewhat.
        if isinstance(exctype, BaseException):
            val = exctype
            exctype = type(val)

        self.last_exception = (exctype, val, tb)

        if tb:
            return 'reraise'
        else:
            return 'exception'

    def byte_SETUP_WITH(self, dest):
        ctxmgr = self.pop()
        self.push(ctxmgr.__exit__)
        ctxmgr_obj = ctxmgr.__enter__()
        self.frame.push_block('with', dest)
        self.push(ctxmgr_obj)

    def byte_WITH_CLEANUP(self):
        # The code here does some weird stack manipulation: the exit function
        # is buried in the stack, and where depends on what's on top of it.
        # Pull out the exit function, and leave the rest in place.
        v = w = None
        u = self.top()
        if u is None:
            exit_func = self.pop(1)
        elif isinstance(u, str):
            if u in ('return', 'continue'):
                exit_func = self.pop(2)
            else:
                exit_func = self.pop(1)
            u = None
        elif issubclass(u, BaseException):
            w, v, u = self.popn(3)
            exit_func = self.pop()
            self.push(w, v, u)
        else:       # pragma: no cover
            raise VirtualMachineError("Confused WITH_CLEANUP")
        exit_ret = exit_func(u, v, w)
        err = (u is not None) and bool(exit_ret)
        if err:
            # An error occurred, and was suppressed
            self.popn(3)
            self.push(None)

    ## Functions

    def byte_MAKE_FUNCTION(self, argc):
        """Make a runtime object from a types.CodeObject, typically in a .pyc file."""
        name = None
        code = self.pop()
        defaults = self.popn(argc)
        globs = self.frame.f_globals
        fn = Function(name, code, globs, defaults, None, self)
        self.push(fn)

    def byte_LOAD_CLOSURE(self, name):
        self.push(self.frame.cells[name])

    def byte_MAKE_CLOSURE(self, argc):
        name = None
        closure, code = self.popn(2)
        defaults = self.popn(argc)
        globs = self.frame.f_globals
        fn = Function(name, code, globs, defaults, closure, self)
        self.push(fn)

    def byte_CALL_FUNCTION(self, arg):
        return self.call_function(arg, [], {})

    def byte_CALL_FUNCTION_VAR(self, arg):
        args = self.pop()
        return self.call_function(arg, args, {})

    def byte_CALL_FUNCTION_KW(self, arg):
        kwargs = self.pop()
        return self.call_function(arg, [], kwargs)

    def byte_CALL_FUNCTION_VAR_KW(self, arg):
        args, kwargs = self.popn(2)
        return self.call_function(arg, args, kwargs)

    def call_function(self, arg, args, kwargs):
        len_kw, len_pos = divmod(arg, 256)
        namedargs = {}
        for i in xrange(len_kw):
            key, val = self.popn(2)
            namedargs[key] = val
        namedargs.update(kwargs)
        posargs = self.popn(len_pos)
        posargs.extend(args)

        #debug('*** call_function stack = %s', self.frame.stack)

        func = self.pop()
        #debug1('*** call_function POPPED %s', func)
        if getattr(func, 'func_name', None) == 'decode_next':
            raise AssertionError('BAD: %s' % func)

        frame = self.frame
        if hasattr(func, 'im_func'):
            # Methods get self as an implicit first parameter.

            #debug('')
            #debug('im_self %r', (func.im_self,))
            #debug('posargs %r', (posargs,))

            if func.im_self is not None:
                posargs.insert(0, func.im_self)

            #debug('posargs AFTER %r', (posargs,))

            # TODO: We have the frame here, but I also want the location.
            # dis has it!

            # The first parameter must be the correct type.
            if not isinstance(posargs[0], func.im_class):
                # Must match Python interpreter to pass unit tests!
                if self.more_info:
                    # More informative error that shows the frame.
                    raise TypeError(
                        'unbound method %s() must be called with %s instance '
                        'as first argument, was called with %s instance '
                        '(frame: %s)' % (
                            func.im_func.func_name,
                            func.im_class.__name__,
                            type(posargs[0]).__name__,
                            #posargs[0],
                            self.frame,
                        )
                    )
                else:
                    raise TypeError(
                        'unbound method %s() must be called with %s instance '
                        'as first argument (got %s instance instead)' % (
                            func.im_func.func_name,
                            func.im_class.__name__,
                            type(posargs[0]).__name__,
                        )
                    )
            func = func.im_func

        # BUG FIX: The callable must be a pyobj.Function, not a native Python
        # function (types.FunctionType).  The latter will be executed using the
        # HOST CPython interpreter rather than the byterun interpreter.

        # Cases:
        # 1. builtin functions like int().  We want to use the host here.
        # 2. User-defined functions from this module.  These are created with
        #    MAKE_FUNCTION, which properly turns them into pyobj.Function.
        # 3. User-defined function from another module.  These are created with
        #    __import__, which yields a native function.
        # 4. pyobj.Generator is on the stack, and you get its next() value.
        #    We should do something smarter.

        # This check is broken!
        # next() and send()  that is a native python function.  We DO NOT need
        # to wrap it.

        do_wrap = False
        #debug1('FUNC %s', dir(func))
        if isinstance(func, types.FunctionType):
          do_wrap = True

        # Hack for case #4.
        if getattr(func, '__doc__', None) == 'DO_NOT_INTERPRET':
          do_wrap = False
          #raise AssertionError

        #debug1('do_wrap: %s', do_wrap)

        if do_wrap:
            #debug1('*** WRAPPING %s', func)
            #debug1('%s', dir(func))
            #debug1('__doc__ %s', func.__doc__)

            defaults = func.func_defaults or ()
            byterun_func = Function(
                    func.func_name, func.func_code, func.func_globals,
                    defaults, func.func_closure, self)
        else:
            byterun_func = func

        #debug1('  Calling: %s', byterun_func)
        retval = byterun_func(*posargs, **namedargs)
        self.push(retval)

    def byte_RETURN_VALUE(self):
        self.return_value = self.pop()
        if self.frame.generator:
            self.frame.generator.finished = True
        return "return"

    def byte_YIELD_VALUE(self):
        self.return_value = self.pop()
        return "yield"

    def byte_YIELD_FROM(self):
        u = self.pop()
        x = self.top()

        try:
            if not isinstance(x, Generator) or u is None:
                # Call next on iterators.
                retval = next(x)
            else:
                retval = x.send(u)
            self.return_value = retval
        except StopIteration as e:
            self.pop()
            self.push(e.value)
        else:
            # YIELD_FROM decrements f_lasti, so that it will be called
            # repeatedly until a StopIteration is raised.
            self.jump(self.frame.f_lasti - 1)
            # Returning "yield" prevents the block stack cleanup code
            # from executing, suspending the frame in its current state.
            return "yield"

    ## Importing

    def byte_IMPORT_NAME(self, name):
        level, fromlist = self.popn(2)
        frame = self.frame

        # NOTE: This can read .pyc files not compiled with OPy!
        # TODO: Respect OPY_PATH

        #debug1('IMPORT name=%s fromlist=%s level=%s', name, fromlist, level)

        mod = __import__(name, frame.f_globals, frame.f_locals, fromlist, level)

        #debug1('IMPORTED %s -> %s' % (name, mod))

        self.push(mod)

    def byte_IMPORT_STAR(self):
        # TODO: this doesn't use __all__ properly.
        mod = self.pop()
        for attr in dir(mod):
            if attr[0] != '_':
                self.frame.f_locals[attr] = getattr(mod, attr)

    def byte_IMPORT_FROM(self, name):
        mod = self.top()
        self.push(getattr(mod, name))

    ## And the rest...

    def byte_EXEC_STMT(self):
        stmt, globs, locs = self.popn(3)
        exec stmt in globs, locs

    def byte_BUILD_CLASS(self):
        name, bases, methods = self.popn(3)
        self.push(type(name, bases, methods))

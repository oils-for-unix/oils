from __future__ import print_function
"""
ovm.py

TODO:

  Define a VM that doens't use exceptions for control flow!
"""

import operator  # for + - * / etc.
import os
import sys
import repr as repr_lib

from .pyvm2 import debug1
from ..lib import dis

# Create a repr that won't overflow.
repr_obj = repr_lib.Repr()
repr_obj.maxother = 120
repper = repr_obj.repr

# Different than log
def debug(msg, *args):
  if not VERBOSE:
    return

  debug1(msg, *args)


VERBOSE = False
#VERBOSE = True


def run_code(vm, code):
    """Main entry point.

    Used by tests and by execfile.
    """
    frame = vm.make_frame(code)
    val = vm.run_frame(frame)
    vm.check_invariants()
    if os.getenv('VM_SUMMARY'):
      debug1('*** OVM executed for %d ticks', vm.num_ticks)
    # If we return the number of ticks here, the unit tests break.
    return val


def run_code_object(code, args, package=None):
    sys.argv = args
    vm = VirtualMachine()
    run_code(vm, code)


# Note: handler is a jump target!
import collections
Block = collections.namedtuple("Block", "type, handler, level")


class Frame(object):
    def __init__(self, f_code, callargs):
        self.f_code = f_code
        self.f_locals = dict(callargs)  # Do we need to make a copy?
        self.stack = []  # expression stack
        self.f_lineno = f_code.co_firstlineno
        self.f_lasti = 0

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
        while len(self.stack) > block.level:
            self.pop()

    def handle_block_stack(self, why, vm):
        """
        After every bytecode that returns why != None, handle everything on the
        block stack.

        The block stack and data stack are shuffled for looping, exception
        handling, or returning.
        """
        assert why != 'yield'

        block = self.block_stack[-1]
        assert block.type == 'loop', block.type

        if why == 'continue':
            self.jump(vm.return_value)  # why is it left in the return value?
            return None

        self.pop_block()
        self._unwind_block(block, vm)

        if why == 'break':
            self.jump(block.handler)
            return None

        raise AssertionError('why = %r' % why)

    def decode_next_raw(self):
        """
        Parse 1 - 3 bytes of bytecode into an instruction and maybe arguments.
        """
        opcode = ord(self.f_code.co_code[self.f_lasti])
        self.f_lasti += 1

        arguments = []
        if opcode >= dis.HAVE_ARGUMENT:
            a1 = self.f_code.co_code[self.f_lasti]
            a2 = self.f_code.co_code[self.f_lasti+1]
            arg = ord(a1) + (ord(a2) << 8)
            self.f_lasti += 2
        else:
            arg = None
        return opcode, arg

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


class VirtualMachineError(Exception):
    """For raising errors in the operation of the VM."""
    pass


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


class VirtualMachine(object):

    def __init__(self, verbose=VERBOSE):
        """
        Args:
          subset: turn off bytecodes that OPy doesn't need (e.g. print
            statement, etc.)
          verbose: turn on logging
        """
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

    # TODO: The frame should only have locals?
    # All globals are constants?  No "rebindable" globals.  (You can have
    # mutable objects but not rebind them.)
    def make_frame(self, code, callargs={}):
        """
        Called by self.run_code and Function.__call__.
        """
        frame = Frame(code, callargs)
        return frame

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

    # Helpers for run_frame
    def _push_frame(self, frame):
        self.frames.append(frame)
        self.frame = frame

    def _pop_frame(self):
        # NOTE: Block(handler) is a jump address.
        #if self.frame.block_stack:
        if False:
            debug1('block stack: %s', self.frame.block_stack)
            raise VirtualMachineError(
                "Block stack still has %d entries" %
                len(self.frame.block_stack))

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
            if self.num_ticks == 300:
              raise VirtualMachineError('Too many ticks')

            opoffset = self.frame.f_lasti  # For logging only
            opcode, arg = self.frame.decode_next_raw()
            inst_name = dis.opname[opcode]
            arguments = []
            if self.verbose:
                self.log_tick(inst_name, arguments, opoffset, linestarts)
                debug1('arg %s', arg)

            # When unwinding the block stack, we need to keep track of why we
            # are doing it.

            # NOTE: In addition to returning why == 'exception', this can also
            # RAISE GuestException from recursive call via call_function.

            why = False

            if inst_name == 'POP_TOP':
              self.pop()

            elif inst_name == 'LOAD_CONST':
              const = self.frame.f_code.co_consts[arg]
              self.push(const)

            elif inst_name == 'STORE_NAME':
              # This is true.  NOTE: dis.hasname is a list.
              #debug1('STORE_NAME %d', opcode)
              name = self.frame.f_code.co_names[arg]
              self.frame.f_locals[name] = self.pop()

            elif inst_name == 'LOAD_NAME':
              #debug1('NAME arg %d', arg)

              name = self.frame.f_code.co_names[arg]
              #debug1('NAME %r', name)
              frame = self.frame
              if name in frame.f_locals:
                  val = frame.f_locals[name]
              elif name == 'print':  # Special case!
                  val = print
              #elif name in frame.f_globals:
              #    val = frame.f_globals[name]
              #elif name in frame.f_builtins:
              #    val = frame.f_builtins[name]
              else:
                  raise NameError("name '%s' is not defined" % name)
              self.push(val)
              # Hack because this is not a global in OVM.
              #if name == 'True':
              #  self.push(True)
              #else:
              #  self.push(self.frame.f_locals[name])

            #
            # Operations
            #
            elif inst_name == 'BINARY_ADD':
              # I guess popn() is slightly faster because you don't decrement.
              # twice?  Even in C?
              x, y = self.popn(2)
              self.push(BINARY_OPERATORS['ADD'](x, y))

            elif inst_name == 'COMPARE_OP':
              x, y = self.popn(2)
              self.push(COMPARE_OPERATORS[arg](x, y))

            #
            # FUNCTIONS / LOOPS
            #
            elif inst_name == 'CALL_FUNCTION':
              # NOTE: There are different bytecodes for
              # CALL_FUNCTION_{VAR,KW,VAR_KW}.
              # I don't thinks we need those in OPy.  I think that is for each
              # combination of foo(*args, **kwargs).  I guess I do need _VAR
              # for log(msg, *args).

              len_kw, len_pos= divmod(arg, 256)
              assert len_kw == 0
              namedargs = {}
              for i in xrange(len_kw):
                  key, val = self.popn(2)
                  namedargs[key] = val

              posargs = self.popn(len_pos)
              #posargs.extend(args)  # For extras

              func = self.pop()  # TODO: assert that it's the print function

              do_wrap = False
              if do_wrap:
                # Hm there needs to be a better way of doing this?
                #callargs = inspect.getcallargs(func, *posargs, **namedargs)
                callargs = None
                frame = self.make_frame(func.func_code, callargs)
                retval = self.run_frame(frame)
              else:
                byterun_func = func
                retval = byterun_func(*posargs, **namedargs)
              self.push(retval)

            elif inst_name == 'RETURN_VALUE':
              why = 'return'

            elif inst_name == 'SETUP_LOOP':
              dest = self.frame.f_lasti + arg  # dis.hasjrel
              self.frame.push_block('loop', dest)

            elif inst_name == 'POP_BLOCK':
              self.frame.pop_block()

            elif inst_name == 'BREAK_LOOP':
              # TODO: Get rid of this; it should be a jump.
              why = 'break'

            #
            # JUMPS
            #
            elif inst_name == 'POP_JUMP_IF_FALSE':
              # NOTE: This is a "superinstruction"; it could just be POP, then
              # JUMP_IF_FALSE.
              val = self.pop()
              if not val:
                self.jump(arg)

            elif inst_name == 'JUMP_ABSOLUTE':
              self.jump(arg)  # dis.hasjabs

            elif inst_name == 'JUMP_FORWARD':
              self.jump(self.frame.f_lasti + arg)  # dis.hasjrel

            #
            # Intentionally ignored imports
            #
            elif inst_name == 'IMPORT_NAME':
              pass
            elif inst_name == 'IMPORT_FROM':
              pass

            else:
              raise AssertionError('OVM not handling %r' % inst_name)

            while why and frame.block_stack:
                debug('WHY %s', why)
                debug('STACK %s', frame.block_stack)
                why = self.frame.handle_block_stack(why, self)

            # TODO: I should be popping and cleaning up blocks here.
            if why:
              break

        self._pop_frame()

        #debug1('num_ticks: %d' % num_ticks)
        return self.return_value

    def check_invariants(self):
      # Check some invariants
      if self.frames:            # pragma: no cover
          raise VirtualMachineError("Frames left over!")
      # NOTE: self.frame is None at the end.
      if self.frame and self.frame.stack:             # pragma: no cover
          raise VirtualMachineError("Data left on stack! %r" % self.frame.stack)

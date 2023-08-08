"""A flow graph representation for Python bytecode"""
from __future__ import print_function

import itertools
import types

from .consts import CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_VARKEYWORDS
from opy.lib import dis


HAS_JREL = set(dis.opname[op] for op in dis.hasjrel)
HAS_JABS = set(dis.opname[op] for op in dis.hasjabs)
OPNUM = dict((name, i) for i, name in enumerate(dis.opname))


def OrderBlocks(start_block, exit_block):
    """Order blocks so that they are emitted in the right order"""
    # Rules:
    # - when a block has a next block, the next block must be emitted just after
    # - when a block has followers (relative jumps), it must be emitted before
    #   them
    # - all reachable blocks must be emitted
    order = []

    # Find all the blocks to be emitted.
    remaining = set()
    todo = [start_block]
    while todo:
        b = todo.pop()
        if b in remaining:
            continue
        remaining.add(b)
        for c in b.get_children():
            if c not in remaining:
                todo.append(c)

    # A block is dominated by another block if that block must be emitted
    # before it.
    dominators = {}
    for b in remaining:
        if __debug__ and b.next:
            assert b is b.next[0].prev[0], (b, b.next)
        # Make sure every block appears in dominators, even if no
        # other block must precede it.
        dominators.setdefault(b, set())
        # preceding blocks dominate following blocks
        for c in b.get_followers():
            while 1:
                dominators.setdefault(c, set()).add(b)
                # Any block that has a next pointer leading to c is also
                # dominated because the whole chain will be emitted at once.
                # Walk backwards and add them all.
                if c.prev and c.prev[0] is not b:
                    c = c.prev[0]
                else:
                    break

    def find_next():
        # Find a block that can be emitted next.
        for b in remaining:
            for c in dominators[b]:
                if c in remaining:
                    break # can't emit yet, dominated by a remaining block
            else:
                return b
        assert 0, 'circular dependency, cannot find next block'

    b = start_block
    while 1:
        order.append(b)
        remaining.discard(b)
        if b.next:
            b = b.next[0]
            continue
        elif b is not exit_block and not b.has_unconditional_transfer():
            order.append(exit_block)
        if not remaining:
            break
        b = find_next()
    return order


def FlattenBlocks(blocks):
    insts = []

    pc = 0
    offsets = {}  # block -> bytecode offset
    for b in blocks:
        offsets[b] = pc
        for inst in b.Instructions():
            insts.append(inst)
            if len(inst) == 1:
                pc += 1
            elif inst[0] != "SET_LINENO":  # arg takes 2 bytes
                pc += 3
    return insts, offsets


def PatchJumps(insts, offsets):
    pc = 0
    for i, inst in enumerate(insts):
        if len(inst) == 1:
            pc += 1
        elif inst[0] != "SET_LINENO":
            pc += 3

        opname = inst[0]

        # Compute jump locations
        if opname in HAS_JREL:
            block_arg = inst[1]
            insts[i] = (opname, offsets[block_arg] - pc)

        elif opname in HAS_JABS:
            block_arg = inst[1]
            insts[i] = (opname, offsets[block_arg])


gBlockCounter = itertools.count()


class Block(object):

    def __init__(self, label=''):
        self.label = label
        self.bid = gBlockCounter.next()
        self.insts = []
        self.outEdges = set()
        self.next = []
        self.prev = []

    # BUG FIX: This is needed for deterministic order in sets (and dicts?).
    # See OrderBlocks() below.  remaining is set() of blocks.  If we rely on
    # the default id(), then the output bytecode is NONDETERMINISTIC.
    def __hash__(self):
        return self.bid

    def __repr__(self):
        if self.label:
            return "<block %s id=%d>" % (self.label, self.bid)
        else:
            return "<block id=%d>" % (self.bid)

    def __str__(self):
        return "<block %s %d:\n%s>" % (
            self.label, self.bid,
            '\n'.join(str(inst) for inst in self.insts))

    def emit(self, inst):
        op = inst[0]
        self.insts.append(inst)

    def Instructions(self):
        return self.insts

    def addOutEdge(self, block):
        self.outEdges.add(block)

    def addNext(self, block):
        self.next.append(block)
        assert len(self.next) == 1, [str(b) for b in self.next]
        block.prev.append(self)
        assert len(block.prev) == 1, [str(b) for b in block.prev]

    _uncond_transfer = ('RETURN_VALUE', 'RAISE_VARARGS',
                        'JUMP_ABSOLUTE', 'JUMP_FORWARD', 'CONTINUE_LOOP',
                        )

    def has_unconditional_transfer(self):
        """Returns True if there is an unconditional transfer to an other block
        at the end of this block. This means there is no risk for the bytecode
        executer to go past this block's bytecode."""
        try:
            op, arg = self.insts[-1]
        except (IndexError, ValueError):
            return
        return op in self._uncond_transfer

    def get_children(self):
        return list(self.outEdges) + self.next

    def get_followers(self):
        """Get the whole list of followers, including the next block."""
        followers = set(self.next)
        # Blocks that must be emitted *after* this one, because of
        # bytecode offsets (e.g. relative jumps) pointing to them.
        for inst in self.insts:
            if inst[0] in HAS_JREL:
                followers.add(inst[1])
        return followers

    def getContainedGraphs(self):
        """Return all graphs contained within this block.

        For example, a MAKE_FUNCTION block will contain a reference to
        the graph for the function body.
        """
        raise AssertionError('unused')
        contained = []
        for inst in self.insts:
            if len(inst) == 1:
                continue
            op = inst[1]
            if hasattr(op, 'graph'):
                contained.append(op.graph)
        return contained


class FlowGraph(object):

    def __init__(self):
        self.current = self.entry = Block()
        self.exit = Block("exit")
        self.blocks = set()
        self.blocks.add(self.entry)
        self.blocks.add(self.exit)

    DEBUG = False

    def startBlock(self, block):
        if self.DEBUG:
            if self.current:
                print("end", repr(self.current))
                print("    next", self.current.next)
                print("    prev", self.current.prev)
                print("   ", self.current.get_children())
            print(repr(block))
        self.current = block

    def nextBlock(self, block=None):
        # XXX think we need to specify when there is implicit transfer
        # from one block to the next.  might be better to represent this
        # with explicit JUMP_ABSOLUTE instructions that are optimized
        # out when they are unnecessary.
        #
        # I think this strategy works: each block has a child
        # designated as "next" which is returned as the last of the
        # children.  because the nodes in a graph are emitted in
        # reverse post order, the "next" block will always be emitted
        # immediately after its parent.
        # Worry: maintaining this invariant could be tricky
        if block is None:
            block = self.newBlock()

        # Note: If the current block ends with an unconditional control
        # transfer, then it is technically incorrect to add an implicit
        # transfer to the block graph. Doing so results in code generation
        # for unreachable blocks.  That doesn't appear to be very common
        # with Python code and since the built-in compiler doesn't optimize
        # it out we don't either.
        self.current.addNext(block)
        self.startBlock(block)

    def newBlock(self):
        b = Block()
        self.blocks.add(b)
        return b

    def startExitBlock(self):
        self.startBlock(self.exit)

    def emit(self, *inst):
        if self.DEBUG:
            print("\t", inst)
        if len(inst) == 2 and isinstance(inst[1], Block):
            self.current.addOutEdge(inst[1])
        self.current.emit(inst)

    def getContainedGraphs(self):
        raise AssertionError('unused')
        l = []
        for b in self.getBlocks():
            l.extend(b.getContainedGraphs())
        return l


class Frame(object):
    """Something that gets turned into a single code object.

    Code objects and consts are mutually recursive.
    """

    def __init__(self, name, filename, optimized=0, klass=None):
        """
        Args:
          klass: Whether we're compiling a class block.
        """
        self.name = name  # name that is put in the code object
        self.filename = filename
        self.flags = (CO_OPTIMIZED | CO_NEWLOCALS) if optimized else 0
        self.klass = klass

        # Mutated by setArgs()
        self.varnames = []
        self.argcount = 0

        # Mutated by setVars().  Free variables found by the symbol table scan,
        # including variables used only in nested scopes, are included here.
        self.freevars = []
        self.cellvars = []

        self.docstring = None

    def setArgs(self, args):
        """Only called by functions, not modules or classes."""
        assert not self.varnames   # Nothing should have been added
        if args:
            self.varnames = list(args)
            self.argcount = len(args)

    def setVars(self, freevars, cellvars):
        self.freevars = freevars
        self.cellvars = cellvars

    def setDocstring(self, doc):
        self.docstring = doc

    def setFlag(self, flag):
        self.flags |= flag

    def checkFlag(self, flag):
        return bool(self.flags & flag)

    def NumLocals(self):
        return len(self.varnames) if self.flags & CO_NEWLOCALS else 0

    def ArgCount(self):
        argcount = self.argcount
        if self.flags & CO_VARKEYWORDS:
            argcount -= 1
        if self.flags & CO_VARARGS:
            argcount -= 1
        return argcount


def ReorderCellVars(frame):
    """Reorder cellvars so the ones in self.varnames are first.

    And prune from freevars (?)
    """
    lookup = set(frame.cellvars)
    remaining = lookup - set(frame.varnames)

    cellvars = [n for n in frame.varnames if n in lookup]
    cellvars.extend(remaining)
    return cellvars


def _NameToIndex(name, L):
    """Return index of name in list, appending if necessary

    This routine uses a list instead of a dictionary, because a
    dictionary can't store two different keys if the keys have the
    same value but different types, e.g. 2 and 2L.  The compiler
    must treat these two separately, so it does an explicit type
    comparison before comparing the values.
    """
    t = type(name)
    for i, item in enumerate(L):
        if t == type(item) and item == name:
            return i
    end = len(L)
    L.append(name)
    return end


class ArgEncoder(object):
    """Replaces arg objects with indices."""

    def __init__(self, klass, consts, names, varnames, closure):
        """
        Args:
          consts ... closure are all potentially mutated!
        """
        self.klass = klass
        self.consts = consts
        self.names = names
        self.varnames = varnames
        self.closure = closure

    def Run(self, insts):
        """Mutates insts."""
        for i, t in enumerate(insts):
            if len(t) == 2:
                opname, oparg = t
                method = self._converters.get(opname, None)
                if method:
                    arg_index = method(self, oparg)
                    insts[i] = opname, arg_index

    # TODO: This should just be a simple switch

    def _convert_LOAD_CONST(self, arg):
        return _NameToIndex(arg, self.consts)

    def _convert_LOAD_FAST(self, arg):
        _NameToIndex(arg, self.names)
        return _NameToIndex(arg, self.varnames)
    _convert_STORE_FAST = _convert_LOAD_FAST
    _convert_DELETE_FAST = _convert_LOAD_FAST

    def _convert_LOAD_NAME(self, arg):
        # TODO: This is wrong.  It leads to too many files.
        # https://github.com/oilshell/oil/issues/180
        if self.klass is None:
            _NameToIndex(arg, self.varnames)
        return _NameToIndex(arg, self.names)

    def _convert_NAME(self, arg):
        if self.klass is None:
            _NameToIndex(arg, self.varnames)
        return _NameToIndex(arg, self.names)
    _convert_STORE_NAME = _convert_NAME
    _convert_DELETE_NAME = _convert_NAME
    _convert_IMPORT_NAME = _convert_NAME
    _convert_IMPORT_FROM = _convert_NAME
    _convert_STORE_ATTR = _convert_NAME
    _convert_LOAD_ATTR = _convert_NAME
    _convert_DELETE_ATTR = _convert_NAME
    _convert_LOAD_GLOBAL = _convert_NAME
    _convert_STORE_GLOBAL = _convert_NAME
    _convert_DELETE_GLOBAL = _convert_NAME

    def _convert_DEREF(self, arg):
        _NameToIndex(arg, self.names)
        _NameToIndex(arg, self.varnames)
        return _NameToIndex(arg, self.closure)
    _convert_LOAD_DEREF = _convert_DEREF
    _convert_STORE_DEREF = _convert_DEREF

    def _convert_LOAD_CLOSURE(self, arg):
        _NameToIndex(arg, self.varnames)
        return _NameToIndex(arg, self.closure)

    _cmp = list(dis.cmp_op)
    def _convert_COMPARE_OP(self, arg):
        return self._cmp.index(arg)

    _converters = {}

    # similarly for other opcodes...

    for name, obj in locals().items():
        if name[:9] == "_convert_":
            opname = name[9:]
            _converters[opname] = obj
    del name, obj, opname


class Assembler(object):
    """Builds co_code and lnotab.

    This class builds the lnotab, which is documented in compile.c.  Here's a
    brief recap:

    For each SET_LINENO instruction after the first one, two bytes are added to
    lnotab.  (In some cases, multiple two-byte entries are added.)  The first
    byte is the distance in bytes between the instruction for the last
    SET_LINENO and the current SET_LINENO.  The second byte is offset in line
    numbers.  If either offset is greater than 255, multiple two-byte entries
    are added -- see compile.c for the delicate details.
    """
    def __init__(self):
        self.code = []
        self.codeOffset = 0
        self.firstline = 0
        self.lastline = 0
        self.lastoff = 0
        self.lnotab = []

    def addCode(self, *args):
        for arg in args:
            self.code.append(chr(arg))
        self.codeOffset += len(args)

    def nextLine(self, lineno):
        if self.firstline == 0:
            self.firstline = lineno
            self.lastline = lineno
        else:
            # compute deltas
            addr = self.codeOffset - self.lastoff
            line = lineno - self.lastline
            # Python assumes that lineno always increases with
            # increasing bytecode address (lnotab is unsigned char).
            # Depending on when SET_LINENO instructions are emitted
            # this is not always true.  Consider the code:
            #     a = (1,
            #          b)
            # In the bytecode stream, the assignment to "a" occurs
            # after the loading of "b".  This works with the C Python
            # compiler because it only generates a SET_LINENO instruction
            # for the assignment.
            if line >= 0:
                push = self.lnotab.append
                while addr > 255:
                    push(255); push(0)
                    addr -= 255
                while line > 255:
                    push(addr); push(255)
                    line -= 255
                    addr = 0
                if addr > 0 or line > 0:
                    push(addr); push(line)
                self.lastline = lineno
                self.lastoff = self.codeOffset

    def Run(self, insts):
        for t in insts:
            opname = t[0]
            if len(t) == 1:
                self.addCode(OPNUM[opname])
            else:
                oparg = t[1]
                if opname == "SET_LINENO":
                    self.nextLine(oparg)
                    continue
                hi, lo = divmod(oparg, 256)
                try:
                    self.addCode(OPNUM[opname], lo, hi)
                except ValueError:
                    print(opname, oparg)
                    print(OPNUM[opname], lo, hi)
                    raise

        bytecode = ''.join(self.code)
        lnotab = ''.join(chr(c) for c in self.lnotab)
        return bytecode, self.firstline, lnotab


class BlockStackDepth(object):
    # XXX 1. need to keep track of stack depth on jumps
    # XXX 2. at least partly as a result, this code is broken

    def Sum(self, insts, debug=0):
        depth = 0
        maxDepth = 0

        for inst in insts:
            opname = inst[0]
            if debug:
                print(inst, end=' ')

            delta = self.effect.get(opname, None)
            if delta is None:
                # now check patterns
                for pat, pat_delta in self.patterns:
                    if opname[:len(pat)] == pat:
                        delta = pat_delta
                        break

            if delta is None:
                meth = getattr(self, opname, None)
                if meth is not None:
                    delta = meth(inst[1])

            if delta is None:
                # Jumps missing here.
                #assert opname in ('POP_JUMP_IF_FALSE', 'SET_LINENO'), opname
                delta = 0

            depth += delta
            maxDepth = max(depth, maxDepth)

            if debug:
                print('%s %s' % (depth, maxDepth))
        return maxDepth

    effect = {
        'POP_TOP': -1,
        'DUP_TOP': 1,
        'LIST_APPEND': -1,
        'SET_ADD': -1,
        'MAP_ADD': -2,
        'SLICE+1': -1,
        'SLICE+2': -1,
        'SLICE+3': -2,
        'STORE_SLICE+0': -1,
        'STORE_SLICE+1': -2,
        'STORE_SLICE+2': -2,
        'STORE_SLICE+3': -3,
        'DELETE_SLICE+0': -1,
        'DELETE_SLICE+1': -2,
        'DELETE_SLICE+2': -2,
        'DELETE_SLICE+3': -3,
        'STORE_SUBSCR': -3,
        'DELETE_SUBSCR': -2,
        # PRINT_EXPR?
        'PRINT_ITEM': -1,
        'RETURN_VALUE': -1,
        'YIELD_VALUE': -1,
        'EXEC_STMT': -3,
        'BUILD_CLASS': -2,
        'STORE_NAME': -1,
        'STORE_ATTR': -2,
        'DELETE_ATTR': -1,
        'STORE_GLOBAL': -1,
        'BUILD_MAP': 1,
        'COMPARE_OP': -1,
        'STORE_FAST': -1,
        'IMPORT_STAR': -1,
        'IMPORT_NAME': -1,
        'IMPORT_FROM': 1,
        'LOAD_ATTR': 0, # unlike other loads
        # close enough...
        'SETUP_EXCEPT': 3,
        'SETUP_FINALLY': 3,
        'FOR_ITER': 1,
        'WITH_CLEANUP': -1,
        }
    # use pattern match
    patterns = [
        ('BINARY_', -1),
        ('LOAD_', 1),
        ]

    def UNPACK_SEQUENCE(self, count):
        return count-1
    def BUILD_TUPLE(self, count):
        return -count+1
    def BUILD_LIST(self, count):
        return -count+1
    def BUILD_SET(self, count):
        return -count+1
    def CALL_FUNCTION(self, argc):
        hi, lo = divmod(argc, 256)
        return -(lo + hi * 2)
    def CALL_FUNCTION_VAR(self, argc):
        return self.CALL_FUNCTION(argc)-1
    def CALL_FUNCTION_KW(self, argc):
        return self.CALL_FUNCTION(argc)-1
    def CALL_FUNCTION_VAR_KW(self, argc):
        return self.CALL_FUNCTION(argc)-2
    def MAKE_FUNCTION(self, argc):
        return -argc
    def MAKE_CLOSURE(self, argc):
        # XXX need to account for free variables too!
        return -argc
    def BUILD_SLICE(self, argc):
        if argc == 2:
            return -1
        elif argc == 3:
            return -2
    def DUP_TOPX(self, argc):
        return argc


class _GraphStackDepth(object):
    """Walk the CFG, computing the maximum stack depth."""

    def __init__(self, depths, exit_block):
        """
        Args:
           depths: is the stack effect of each basic block.  Then find the path
           through the code with the largest total effect.
        """
        self.depths = depths
        self.exit_block = exit_block
        self.seen = set()

    def Max(self, block, d):
        if block in self.seen:
            return d
        self.seen.add(block)

        d += self.depths[block]

        children = block.get_children()
        if children:
            return max(self.Max(c, d) for c in children)

        if block.label == "exit":
            return d

        return self.Max(self.exit_block, d)


def MaxStackDepth(block_depths, entry_block, exit_block):
    """Compute maximum stack depth for any path through the CFG."""
    g = _GraphStackDepth(block_depths, exit_block)
    return g.Max(entry_block, 0)


def MakeCodeObject(frame, graph, comp_opt):
    """Order blocks, encode instructions, and create types.CodeType().

    Called by Compile below, and also recursively by ArgEncoder.
    """
    # Compute stack depth per basic block.
    b = BlockStackDepth()
    block_depths = {
        block: b.Sum(block.Instructions()) for block in graph.blocks
    }

    stacksize = MaxStackDepth(block_depths, graph.entry, graph.exit)

    # Order blocks so jump offsets can be encoded.
    blocks = OrderBlocks(graph.entry, graph.exit)

    # Produce a stream of initial instructions.
    insts, block_offsets = FlattenBlocks(blocks)

    # Now that we know the offsets, make another pass.
    PatchJumps(insts, block_offsets)

    # What variables should be available at runtime?

    cellvars = ReorderCellVars(frame)

    # NOTE: Modules docstrings are assigned to __doc__ in pycodegen.py.visitModule.
    consts = []
    if comp_opt.emit_docstring:
      consts.append(frame.docstring)

    names = []
    # The closure list is used to track the order of cell variables and
    # free variables in the resulting code object.  The offsets used by
    # LOAD_CLOSURE/LOAD_DEREF refer to both kinds of variables.
    closure = cellvars + frame.freevars

    # Convert arguments from symbolic to concrete form.
    enc = ArgEncoder(frame.klass, consts, names, frame.varnames,
                     closure)
    # Mutates not only insts, but also appends to consts, names, etc.
    enc.Run(insts)

    # Binary encoding.
    a = Assembler()
    bytecode, firstline, lnotab = a.Run(insts)

    return types.CodeType(
        frame.ArgCount(), frame.NumLocals(), stacksize, frame.flags,
        bytecode,
        tuple(consts),
        tuple(names),
        tuple(frame.varnames),
        frame.filename, frame.name, firstline,
        lnotab,
        tuple(frame.freevars),
        tuple(cellvars))

#!/usr/bin/env python
"""
unpickle.py: A subset of unpickling code from pickle.py.

- We don't want to ship the pickler.
- We only need to handle the v2 protocol
- We only need to handle the parts of the protocol that we use.

For reference, the _RuntimeType hierarchy seems to require 15 unique
instructions + PROTO and STOP, which are trivial.
"""

import marshal
import sys

mloads = marshal.loads


# Copied from types.py
class _C:
    def _m(self): pass

ClassType = type(_C)


# NOTE: I think INST and OBJ aren't used?  We want NEWOBJ.
class _EmptyClass:
    pass


# Pickle opcodes.  See pickletools.py for extensive docs.  The listing
# here is in kind-of alphabetical order of 1-character pickle code.
# pickletools groups them by purpose.

MARK            = '('   # push special markobject on stack
STOP            = '.'   # every pickle ends with STOP
POP             = '0'   # discard topmost stack item
POP_MARK        = '1'   # discard stack top through topmost markobject
DUP             = '2'   # duplicate top stack item
FLOAT           = 'F'   # push float object; decimal string argument
INT             = 'I'   # push integer or bool; decimal string argument
BININT          = 'J'   # push four-byte signed int
BININT1         = 'K'   # push 1-byte unsigned int
LONG            = 'L'   # push long; decimal string argument
BININT2         = 'M'   # push 2-byte unsigned int
NONE            = 'N'   # push None
PERSID          = 'P'   # push persistent object; id is taken from string arg
BINPERSID       = 'Q'   #  "       "         "  ;  "  "   "     "  stack
REDUCE          = 'R'   # apply callable to argtuple, both on stack
STRING          = 'S'   # push string; NL-terminated string argument
BINSTRING       = 'T'   # push string; counted binary string argument
SHORT_BINSTRING = 'U'   #  "     "   ;    "      "       "      " < 256 bytes
UNICODE         = 'V'   # push Unicode string; raw-unicode-escaped'd argument
BINUNICODE      = 'X'   #   "     "       "  ; counted UTF-8 string argument
APPEND          = 'a'   # append stack top to list below it
BUILD           = 'b'   # call __setstate__ or __dict__.update()
GLOBAL          = 'c'   # push self.find_class(modname, name); 2 string args
DICT            = 'd'   # build a dict from stack items
EMPTY_DICT      = '}'   # push empty dict
APPENDS         = 'e'   # extend list on stack by topmost stack slice
GET             = 'g'   # push item from memo on stack; index is string arg
BINGET          = 'h'   #   "    "    "    "   "   "  ;   "    " 1-byte arg
INST            = 'i'   # build & push class instance
LONG_BINGET     = 'j'   # push item from memo on stack; index is 4-byte arg
LIST            = 'l'   # build list from topmost stack items
EMPTY_LIST      = ']'   # push empty list
OBJ             = 'o'   # build & push class instance
PUT             = 'p'   # store stack top in memo; index is string arg
BINPUT          = 'q'   #   "     "    "   "   " ;   "    " 1-byte arg
LONG_BINPUT     = 'r'   #   "     "    "   "   " ;   "    " 4-byte arg
SETITEM         = 's'   # add key+value pair to dict
TUPLE           = 't'   # build tuple from topmost stack items
EMPTY_TUPLE     = ')'   # push empty tuple
SETITEMS        = 'u'   # modify dict by adding topmost key+value pairs
BINFLOAT        = 'G'   # push float; arg is 8-byte float encoding

TRUE            = 'I01\n'  # not an opcode; see INT docs in pickletools.py
FALSE           = 'I00\n'  # not an opcode; see INT docs in pickletools.py

# Protocol 2

PROTO           = '\x80'  # identify pickle protocol
NEWOBJ          = '\x81'  # build object by applying cls.__new__ to argtuple
EXT1            = '\x82'  # push object from extension registry; 1-byte index
EXT2            = '\x83'  # ditto, but 2-byte index
EXT4            = '\x84'  # ditto, but 4-byte index
TUPLE1          = '\x85'  # build 1-tuple from stack top
TUPLE2          = '\x86'  # build 2-tuple from two topmost stack items
TUPLE3          = '\x87'  # build 3-tuple from three topmost stack items
NEWTRUE         = '\x88'  # push True
NEWFALSE        = '\x89'  # push False
LONG1           = '\x8a'  # push long from < 256 bytes
LONG4           = '\x8b'  # push really big long


# An instance of _Stop is raised by Unpickler.load_stop() in response to
# the STOP opcode, passing the object that is the result of unpickling.
class _Stop(Exception):
    def __init__(self, value):
        self.value = value


class Unpickler(object):

    def __init__(self, file):
        """This takes a file-like object for reading a pickle data stream.

        The protocol version of the pickle is detected automatically, so no
        proto argument is needed.

        The file-like object must have two methods, a read() method that
        takes an integer argument, and a readline() method that requires no
        arguments.  Both methods should return a string.  Thus file-like
        object can be a file object opened for reading, a StringIO object,
        or any other custom object that meets this interface.
        """
        self.readline = file.readline
        self.read = file.read
        self.memo = {}

    def load(self):
        """Read a pickled object representation from the open file.

        Return the reconstituted object hierarchy specified in the file.
        """
        self.mark = object() # any new unique object
        self.stack = []
        self.append = self.stack.append
        read = self.read
        dispatch = self.dispatch
        try:
            while 1:
                key = read(1)
                dispatch[key](self)
        except _Stop as stopinst:
            return stopinst.value

    # Return largest index k such that self.stack[k] is self.mark.
    # If the stack doesn't contain a mark, eventually raises IndexError.
    # This could be sped by maintaining another stack, of indices at which
    # the mark appears.  For that matter, the latter stack would suffice,
    # and we wouldn't need to push mark objects on self.stack at all.
    # Doing so is probably a good thing, though, since if the pickle is
    # corrupt (or hostile) we may get a clue from finding self.mark embedded
    # in unpickled objects.
    def marker(self):
        stack = self.stack
        mark = self.mark
        k = len(stack)-1
        while stack[k] is not mark: k = k-1
        return k

    dispatch = {}

    def load_eof(self):
        raise EOFError
    dispatch[''] = load_eof

    def load_proto(self):
        proto = ord(self.read(1))
        if not 0 <= proto <= 2:
            raise ValueError, "unsupported pickle protocol: %d" % proto
    dispatch[PROTO] = load_proto

    def load_persid(self):
        pid = self.readline()[:-1]
        self.append(self.persistent_load(pid))
    dispatch[PERSID] = load_persid

    def load_binpersid(self):
        pid = self.stack.pop()
        self.append(self.persistent_load(pid))
    dispatch[BINPERSID] = load_binpersid

    def load_none(self):
        self.append(None)
    dispatch[NONE] = load_none

    def load_false(self):
        self.append(False)
    dispatch[NEWFALSE] = load_false

    def load_true(self):
        self.append(True)
    dispatch[NEWTRUE] = load_true

    def load_int(self):
        data = self.readline()
        if data == FALSE[1:]:
            val = False
        elif data == TRUE[1:]:
            val = True
        else:
            try:
                val = int(data)
            except ValueError:
                val = long(data)
        self.append(val)
    dispatch[INT] = load_int

    def load_binint(self):
        self.append(mloads('i' + self.read(4)))
    dispatch[BININT] = load_binint

    def load_binint1(self):
        self.append(ord(self.read(1)))
    dispatch[BININT1] = load_binint1

    def load_binint2(self):
        self.append(mloads('i' + self.read(2) + '\000\000'))
    dispatch[BININT2] = load_binint2

    def load_long(self):
        self.append(long(self.readline()[:-1], 0))
    dispatch[LONG] = load_long

    # Commented out because decode_long() depends on _binascii.
    #def load_long1(self):

    #def load_long4(self):

    def load_float(self):
        self.append(float(self.readline()[:-1]))
    dispatch[FLOAT] = load_float

    # Commented out because of struct.unpack.
    #def load_binfloat(self):

    def load_string(self):
        rep = self.readline()[:-1]
        for q in "\"'": # double or single quote
            if rep.startswith(q):
                if len(rep) < 2 or not rep.endswith(q):
                    raise ValueError, "insecure string pickle"
                rep = rep[len(q):-len(q)]
                break
        else:
            raise ValueError, "insecure string pickle"
        self.append(rep.decode("string-escape"))
    dispatch[STRING] = load_string

    def load_binstring(self):
        len = mloads('i' + self.read(4))
        self.append(self.read(len))
    dispatch[BINSTRING] = load_binstring

    def load_unicode(self):
        self.append(unicode(self.readline()[:-1],'raw-unicode-escape'))
    dispatch[UNICODE] = load_unicode

    def load_binunicode(self):
        len = mloads('i' + self.read(4))
        self.append(unicode(self.read(len),'utf-8'))
    dispatch[BINUNICODE] = load_binunicode

    def load_short_binstring(self):
        len = ord(self.read(1))
        self.append(self.read(len))
    dispatch[SHORT_BINSTRING] = load_short_binstring

    def load_tuple(self):
        k = self.marker()
        self.stack[k:] = [tuple(self.stack[k+1:])]
    dispatch[TUPLE] = load_tuple

    def load_empty_tuple(self):
        self.stack.append(())
    dispatch[EMPTY_TUPLE] = load_empty_tuple

    def load_tuple1(self):
        self.stack[-1] = (self.stack[-1],)
    dispatch[TUPLE1] = load_tuple1

    def load_tuple2(self):
        self.stack[-2:] = [(self.stack[-2], self.stack[-1])]
    dispatch[TUPLE2] = load_tuple2

    def load_tuple3(self):
        self.stack[-3:] = [(self.stack[-3], self.stack[-2], self.stack[-1])]
    dispatch[TUPLE3] = load_tuple3

    def load_empty_list(self):
        self.stack.append([])
    dispatch[EMPTY_LIST] = load_empty_list

    def load_empty_dictionary(self):
        self.stack.append({})
    dispatch[EMPTY_DICT] = load_empty_dictionary

    def load_list(self):
        k = self.marker()
        self.stack[k:] = [self.stack[k+1:]]
    dispatch[LIST] = load_list

    def load_dict(self):
        k = self.marker()
        d = {}
        items = self.stack[k+1:]
        for i in range(0, len(items), 2):
            key = items[i]
            value = items[i+1]
            d[key] = value
        self.stack[k:] = [d]
    dispatch[DICT] = load_dict

    # INST and OBJ differ only in how they get a class object.  It's not
    # only sensible to do the rest in a common routine, the two routines
    # previously diverged and grew different bugs.
    # klass is the class to instantiate, and k points to the topmost mark
    # object, following which are the arguments for klass.__init__.
    def _instantiate(self, klass, k):
        args = tuple(self.stack[k+1:])
        del self.stack[k:]
        instantiated = 0
        if (not args and
                type(klass) is ClassType and
                not hasattr(klass, "__getinitargs__")):
            try:
                value = _EmptyClass()
                value.__class__ = klass
                instantiated = 1
            except RuntimeError:
                # In restricted execution, assignment to inst.__class__ is
                # prohibited
                pass
        if not instantiated:
            try:
                value = klass(*args)
            except TypeError, err:
                raise TypeError, "in constructor for %s: %s" % (
                    klass.__name__, str(err)), sys.exc_info()[2]
        self.append(value)

    def load_inst(self):
        module = self.readline()[:-1]
        name = self.readline()[:-1]
        klass = self.find_class(module, name)
        self._instantiate(klass, self.marker())
    dispatch[INST] = load_inst

    def load_obj(self):
        # Stack is ... markobject classobject arg1 arg2 ...
        k = self.marker()
        klass = self.stack.pop(k+1)
        self._instantiate(klass, k)
    dispatch[OBJ] = load_obj

    def load_newobj(self):
        args = self.stack.pop()
        cls = self.stack[-1]
        obj = cls.__new__(cls, *args)
        self.stack[-1] = obj
    dispatch[NEWOBJ] = load_newobj

    def load_global(self):
        module = self.readline()[:-1]
        name = self.readline()[:-1]
        klass = self.find_class(module, name)
        self.append(klass)
    dispatch[GLOBAL] = load_global

    def find_class(self, module, name):
        # Subclasses may override this
        __import__(module)
        mod = sys.modules[module]
        klass = getattr(mod, name)
        return klass

    def load_reduce(self):
        stack = self.stack
        args = stack.pop()
        func = stack[-1]
        value = func(*args)
        stack[-1] = value
    dispatch[REDUCE] = load_reduce

    def load_pop(self):
        del self.stack[-1]
    dispatch[POP] = load_pop

    def load_pop_mark(self):
        k = self.marker()
        del self.stack[k:]
    dispatch[POP_MARK] = load_pop_mark

    def load_dup(self):
        self.append(self.stack[-1])
    dispatch[DUP] = load_dup

    def load_get(self):
        self.append(self.memo[self.readline()[:-1]])
    dispatch[GET] = load_get

    def load_binget(self):
        i = ord(self.read(1))
        self.append(self.memo[repr(i)])
    dispatch[BINGET] = load_binget

    def load_long_binget(self):
        i = mloads('i' + self.read(4))
        self.append(self.memo[repr(i)])
    dispatch[LONG_BINGET] = load_long_binget

    def load_put(self):
        self.memo[self.readline()[:-1]] = self.stack[-1]
    dispatch[PUT] = load_put

    def load_binput(self):
        i = ord(self.read(1))
        self.memo[repr(i)] = self.stack[-1]
    dispatch[BINPUT] = load_binput

    def load_long_binput(self):
        i = mloads('i' + self.read(4))
        self.memo[repr(i)] = self.stack[-1]
    dispatch[LONG_BINPUT] = load_long_binput

    def load_append(self):
        stack = self.stack
        value = stack.pop()
        list = stack[-1]
        list.append(value)
    dispatch[APPEND] = load_append

    def load_appends(self):
        stack = self.stack
        mark = self.marker()
        list = stack[mark - 1]
        list.extend(stack[mark + 1:])
        del stack[mark:]
    dispatch[APPENDS] = load_appends

    def load_setitem(self):
        stack = self.stack
        value = stack.pop()
        key = stack.pop()
        dict = stack[-1]
        dict[key] = value
    dispatch[SETITEM] = load_setitem

    def load_setitems(self):
        stack = self.stack
        mark = self.marker()
        dict = stack[mark - 1]
        for i in range(mark + 1, len(stack), 2):
            dict[stack[i]] = stack[i + 1]

        del stack[mark:]
    dispatch[SETITEMS] = load_setitems

    def load_build(self):
        stack = self.stack
        state = stack.pop()
        inst = stack[-1]
        setstate = getattr(inst, "__setstate__", None)
        if setstate:
            setstate(state)
            return
        slotstate = None
        if isinstance(state, tuple) and len(state) == 2:
            state, slotstate = state
        if state:
            try:
                d = inst.__dict__
                try:
                    for k, v in state.iteritems():
                        d[intern(k)] = v
                # keys in state don't have to be strings
                # don't blow up, but don't go out of our way
                except TypeError:
                    d.update(state)

            except RuntimeError:
                # XXX In restricted execution, the instance's __dict__
                # is not accessible.  Use the old way of unpickling
                # the instance variables.  This is a semantic
                # difference when unpickling in restricted
                # vs. unrestricted modes.
                # Note, however, that cPickle has never tried to do the
                # .update() business, and always uses
                #     PyObject_SetItem(inst.__dict__, key, value) in a
                # loop over state.items().
                for k, v in state.items():
                    setattr(inst, k, v)
        if slotstate:
            for k, v in slotstate.items():
                setattr(inst, k, v)
    dispatch[BUILD] = load_build

    def load_mark(self):
        self.append(self.mark)
    dispatch[MARK] = load_mark

    def load_stop(self):
        value = self.stack.pop()
        raise _Stop(value)
    dispatch[STOP] = load_stop


def load_v2_subset(f):
    """Turn a pickle into an object.
    
    Handles a subset of the v2 protocol.
    """
    return Unpickler(f).load()

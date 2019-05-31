# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""This module defines the data structures used to represent a grammar.

These are a bit arcane because they are derived from the data
structures used by Python's 'pgen' parser generator.

There's also a table here mapping operators to their names in the
token module; the Python tokenize module reports all operators as the
fallback token code OP, but the parser needs the actual token code.

"""

# Python imports
import collections
import marshal

from . import token
from core.util import log


class Grammar(object):
    """Pgen parsing tables conversion class.

    Once initialized, this class supplies the grammar tables for the
    parsing engine implemented by parse.py.  The parsing engine
    accesses the instance variables directly.  The class here does not
    provide initialization of the tables; several subclasses exist to
    do this (see the conv and pgen modules).

    The load() method reads the tables from a pickle file, which is
    much faster than the other ways offered by subclasses.  The pickle
    file is written by calling dump() (after loading the grammar
    tables using a subclass).  The report() method prints a readable
    representation of the tables to stdout, for debugging.

    The instance variables are as follows:

    symbol2number -- a dict mapping symbol names to numbers.  Symbol
                     numbers are always 256 or higher, to distinguish
                     them from token numbers, which are between 0 and
                     255 (inclusive).

    number2symbol -- a dict mapping numbers to symbol names;
                     these two are each other's inverse.

    states        -- a list of DFAs, where each DFA is a list of
                     states, each state is a list of arcs, and each
                     arc is a (i, j) pair where i is a label and j is
                     a state number.  The DFA number is the index into
                     this list.  (This name is slightly confusing.)
                     Final states are represented by a special arc of
                     the form (0, j) where j is its own state number.

    dfas          -- a dict mapping symbol numbers to (DFA, first)
                     pairs, where DFA is an item from the states list
                     above, and first is a set of tokens that can
                     begin this grammar rule (represented by a dict
                     whose values are always 1).

    labels        -- a list of (x, y) pairs where x is either a token
                     number or a symbol number, and y is either None
                     or a string; the strings are keywords.  The label
                     number is the index in this list; label numbers
                     are used to mark state transitions (arcs) in the
                     DFAs.

                     Oil patch: this became List[int] where int is the
                     token/symbol number.

    start         -- the number of the grammar's start symbol.

    keywords      -- a dict mapping keyword strings to arc labels.

    tokens        -- a dict mapping token numbers to arc labels.

    """

    def __init__(self):
        self.symbol2number = {}
        self.number2symbol = {}
        self.states = []
        self.dfas = {}
        # Oil patch: used to be [(0, "EMPTY")].  I suppose 0 is a special value?
        # Or is it ENDMARKER?
        self.labels = [0]
        self.keywords = {}
        self.tokens = {}
        self.symbol2label = {}
        self.start = 256

    def dump(self, filename):
        """Dump the grammar tables to a marshal file.

        Oil patch: changed pickle to marshal.

        dump() recursively changes all dict to OrderedDict, so the pickled file
        is not exactly the same as what was passed in to dump(). load() uses the
        pickled file to create the tables, but  only changes OrderedDict to dict
        at the top level; it does not recursively change OrderedDict to dict.
        So, the loaded tables are different from the original tables that were
        passed to load() in that some of the OrderedDict (from the pickled file)
        are not changed back to dict. For parsing, this has no effect on
        performance because OrderedDict uses dict's __getitem__ with nothing in
        between.
        """
        #self.report()
        with open(filename, "wb") as f:
            f.write(self.MARSHAL_HEADER)
            marshal.dump(self.symbol2number, f)
            marshal.dump(self.number2symbol, f)
            marshal.dump(self.states, f)
            marshal.dump(self.dfas, f)
            marshal.dump(self.labels, f)
            marshal.dump(self.keywords, f)
            marshal.dump(self.tokens, f)
            marshal.dump(self.symbol2label, f)
            marshal.dump(self.start, f)

    MARSHAL_HEADER = 'PGEN2\n'  # arbitrary header

    def load(self, f):
        h = f.read(len(self.MARSHAL_HEADER))
        if h != self.MARSHAL_HEADER:
          raise RuntimeError('Invalid header %r' % h)

        self.symbol2number = marshal.load(f)
        assert isinstance(self.symbol2number, dict), self.symbol2number
        self.number2symbol = marshal.load(f)
        assert isinstance(self.number2symbol, dict), self.number2symbol
        self.states = marshal.load(f)
        self.dfas = marshal.load(f)
        self.labels = marshal.load(f)
        self.keywords = marshal.load(f)
        self.tokens = marshal.load(f)
        self.symbol2label = marshal.load(f)
        self.start = marshal.load(f)
        #self.report()

    def copy(self):
        """
        Copy the grammar.
        """
        new = self.__class__()
        for dict_attr in ("symbol2number", "number2symbol", "dfas", "keywords",
                          "tokens", "symbol2label"):
            setattr(new, dict_attr, getattr(self, dict_attr).copy())
        new.labels = self.labels[:]
        new.states = self.states[:]
        new.start = self.start
        return new

    def report(self):
        """Dump the grammar tables to standard output, for debugging."""
        from pprint import pprint
        log("symbol2number: %d entries", len(self.symbol2number))
        log("number2symbol: %d entries", len(self.number2symbol))
        log("states: %d entries", len(self.states))
        log("dfas: %d entries", len(self.dfas))
        return
        print("labels")
        pprint(self.labels)
        print("keywords")
        pprint(self.labels)
        print("tokens")
        pprint(self.tokens)
        print("symbol2label")
        pprint(self.symbol2label)
        print("start", self.start)


def _make_deterministic(top):
    if isinstance(top, dict):
        return collections.OrderedDict(
            sorted(((k, _make_deterministic(v)) for k, v in top.items())))
    if isinstance(top, list):
        return [_make_deterministic(e) for e in top]
    if isinstance(top, tuple):
        return tuple(_make_deterministic(e) for e in top)
    return top


# Map from operator to number (since tokenize doesn't do this)

opmap_raw = """
( LPAR
) RPAR
[ LSQB
] RSQB
: COLON
, COMMA
; SEMI
+ PLUS
- MINUS
* STAR
/ SLASH
| VBAR
& AMPER
< LESS
> GREATER
= EQUAL
. DOT
% PERCENT
` BACKQUOTE
{ LBRACE
} RBRACE
@ AT
@= ATEQUAL
== EQEQUAL
!= NOTEQUAL
<> NOTEQUAL
<= LESSEQUAL
>= GREATEREQUAL
~ TILDE
^ CIRCUMFLEX
<< LEFTSHIFT
>> RIGHTSHIFT
** DOUBLESTAR
+= PLUSEQUAL
-= MINEQUAL
*= STAREQUAL
/= SLASHEQUAL
%= PERCENTEQUAL
&= AMPEREQUAL
|= VBAREQUAL
^= CIRCUMFLEXEQUAL
<<= LEFTSHIFTEQUAL
>>= RIGHTSHIFTEQUAL
**= DOUBLESTAREQUAL
// DOUBLESLASH
//= DOUBLESLASHEQUAL
-> RARROW
"""

opmap = {}
for line in opmap_raw.splitlines():
    if line:
        op, name = line.split()
        opmap[op] = getattr(token, name)

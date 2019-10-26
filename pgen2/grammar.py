# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""This module defines the data structures used to represent a grammar.

These are a bit arcane because they are derived from the data
structures used by Python's 'pgen' parser generator.

There's also a table here mapping operators to their names in the
token module; the Python tokenize module reports all operators as the
fallback token code OP, but the parser needs the actual token code.

"""

import marshal

from core.util import log
from mycpp import mylib

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from typing import IO, Dict, List, Tuple

  # Type aliases
  arc_t = Tuple[int, int]
  first_t = Dict[int, int]
  states_t = List[List[arc_t]]
  dfa_t = Tuple[states_t, first_t]


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
        # type: () -> None
        self.symbol2number = {}  # type: Dict[str, int]
        self.number2symbol = {}  # type: Dict[int, str]

        # TODO: See MakeGrammar in pgen2/pgen.py
        # To see the type
        # states: List[List[arcs]]
        # arc: (int, int)
        # dfs = Dict[int, Tuple[states, ...]]

        self.states = []  # type: states_t
        self.dfas = {}  # type: Dict[int, dfa_t]
        # Oil patch: used to be [(0, "EMPTY")].  I suppose 0 is a special value?
        # Or is it ENDMARKER?
        self.labels = [0]  # type: List[int]
        self.keywords = {}  # type: Dict[str, int]
        self.tokens = {}  # type: Dict[int, int]
        self.symbol2label = {}  # type: Dict[str, int]
        self.start = 256

    if mylib.PYTHON:
      def dump(self, f):
          # type: (IO[str]) -> None
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
          # Hack to get rid of Id_t
          labels = [int(i) for i in self.labels]
          tokens = dict((int(k), v) for (k, v) in self.tokens.iteritems())

          #self.report()
          payload = (
            self.MARSHAL_HEADER,
            self.symbol2number,
            self.number2symbol,
            self.states,
            self.dfas,
            labels,
            self.keywords,
            tokens,
            self.symbol2label,
            self.start,
          )  # tuple
          marshal.dump(payload, f)  # version 2 is latest

      def dump_nonterminals_py(self, f):
          # type: (IO[str]) -> None
          """Write a Python module with nonterminals.
          
          Analogous to the 'symbol' module in Python.
          """
          f.write('# This code is generated by pgen2/grammar.py\n\n')
          for num in sorted(self.number2symbol):
            name = self.number2symbol[num]
            f.write('%s = %d\n' % (name, num))

      def dump_nonterminals_cpp(self, f):
          # type: (IO[str]) -> None
          """Write a Python module with nonterminals.
          
          Analogous to the 'symbol' module in Python.
          """
          f.write("""\
// This code is generated by pgen2/grammar.py

namespace grammar_nt {
""")
          for num in sorted(self.number2symbol):
            name = self.number2symbol[num]
            f.write('  const int %s = %d;\n' % (name, num))
          f.write("""\

}  // namespace grammar_nt
""")

      MARSHAL_HEADER = 'PGEN2\n'  # arbitrary header

      def loads(self, s):
          # type: (str) -> None
          """Load the grammar from a string.

          We have to use a string rather than a file because the marshal module
          doesn't "fake" support zipimport files.
          """
          payload = marshal.loads(s)
          if payload[0] != self.MARSHAL_HEADER:
            raise RuntimeError('Invalid header %r' % payload[0])

          ( _,
            self.symbol2number,
            self.number2symbol,
            self.states,
            self.dfas,
            self.labels,
            self.keywords,
            self.tokens,
            self.symbol2label,
            self.start,
          ) = payload
          #self.report()

          assert isinstance(self.symbol2number, dict), self.symbol2number
          assert isinstance(self.number2symbol, dict), self.number2symbol

      def report(self):
          # type: () -> None
          """Dump the grammar tables to standard output, for debugging."""
          log("symbol2number: %d entries", len(self.symbol2number))
          log("number2symbol: %d entries", len(self.number2symbol))
          log("states: %d entries", len(self.states))
          log("dfas: %d entries", len(self.dfas))
          return
          from pprint import pprint
          print("labels")
          pprint(self.labels)
          print("keywords")
          pprint(self.labels)
          print("tokens")
          pprint(self.tokens)
          print("symbol2label")
          pprint(self.symbol2label)
          print("start", self.start)

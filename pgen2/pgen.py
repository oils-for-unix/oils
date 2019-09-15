# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Pgen imports
#import grammar, token, tokenize
# NOTE: Need these special versions of token/tokenize for BACKQUOTE and such.
from . import grammar, token, tokenize
from core.util import log


class PythonTokDef(object):

  def GetTerminalNum(self, label):
    """ e.g. NAME -> 1 """
    itoken = getattr(token, label, None)
    assert isinstance(itoken, int), label
    assert itoken in token.tok_name, label
    return itoken

  def GetKeywordNum(self, value):
    """
    e.g 'xor' -> Id.Expr_Xor

    Python doesn't have this, but Oil does.  Returns None if not found.
    """
    return None

  def GetOpNum(self, op_str):
    """
    e.g '(' -> LPAR

    Raises an exception if it's not found.
    """
    return token.opmap[op_str]


class ParserGenerator(object):

    def __init__(self, lexer):
        self.lexer = lexer

    def parse(self):
        self.gettoken()  # Initialize lookahead

        dfas = {}
        startsymbol = None
        # MSTART: (NEWLINE | RULE)* ENDMARKER
        while self.type != token.ENDMARKER:
            while self.type == token.NEWLINE:
                self.gettoken()
            # RULE: NAME ':' RHS NEWLINE
            name = self.expect(token.NAME)
            self.expect(token.OP, ":")
            a, z = self.parse_rhs()
            self.expect(token.NEWLINE)
            #self.dump_nfa(name, a, z)
            dfa = self.make_dfa(a, z)
            #self.dump_dfa(name, dfa)
            oldlen = len(dfa)
            self.simplify_dfa(dfa)
            newlen = len(dfa)
            dfas[name] = dfa
            #print name, oldlen, newlen
            if startsymbol is None:
                startsymbol = name
        return dfas, startsymbol

    def make_dfa(self, start, finish):
        # To turn an NFA into a DFA, we define the states of the DFA
        # to correspond to *sets* of states of the NFA.  Then do some
        # state reduction.  Let's represent sets as dicts with 1 for
        # values.
        assert isinstance(start, NFAState)
        assert isinstance(finish, NFAState)
        def closure(state):
            base = {}
            addclosure(state, base)
            return base
        def addclosure(state, base):
            assert isinstance(state, NFAState)
            if state in base:
                return
            base[state] = 1
            for label, next in state.arcs:
                if label is None:
                    addclosure(next, base)
        states = [DFAState(closure(start), finish)]
        for state in states: # NB states grows while we're iterating
            arcs = {}
            for nfastate in state.nfaset:
                for label, next in nfastate.arcs:
                    if label is not None:
                        addclosure(next, arcs.setdefault(label, {}))
            for label, nfaset in sorted(arcs.items()):
                for st in states:
                    if st.nfaset == nfaset:
                        break
                else:
                    st = DFAState(nfaset, finish)
                    states.append(st)
                state.addarc(st, label)
        return states # List of DFAState instances; first one is start

    def dump_nfa(self, name, start, finish):
        print("Dump of NFA for", name)
        todo = [start]
        for i, state in enumerate(todo):
            print("  State", i, state is finish and "(final)" or "")
            for label, next in state.arcs:
                if next in todo:
                    j = todo.index(next)
                else:
                    j = len(todo)
                    todo.append(next)
                if label is None:
                    print("    -> %d" % j)
                else:
                    print("    %s -> %d" % (label, j))

    def dump_dfa(self, name, dfa):
        print("Dump of DFA for", name)
        for i, state in enumerate(dfa):
            print("  State", i, state.isfinal and "(final)" or "")
            for label, next in sorted(state.arcs.items()):
                print("    %s -> %d" % (label, dfa.index(next)))

    def simplify_dfa(self, dfa):
        # This is not theoretically optimal, but works well enough.
        # Algorithm: repeatedly look for two states that have the same
        # set of arcs (same labels pointing to the same nodes) and
        # unify them, until things stop changing.

        # dfa is a list of DFAState instances
        changes = True
        while changes:
            changes = False
            for i, state_i in enumerate(dfa):
                for j in range(i+1, len(dfa)):
                    state_j = dfa[j]
                    if state_i == state_j:
                        #print "  unify", i, j
                        del dfa[j]
                        for state in dfa:
                            state.unifystate(state_j, state_i)
                        changes = True
                        break

    def parse_rhs(self):
        # RHS: ALT ('|' ALT)*
        a, z = self.parse_alt()
        if self.value != "|":
            return a, z
        else:
            aa = NFAState()
            zz = NFAState()
            aa.addarc(a)
            z.addarc(zz)
            while self.value == "|":
                self.gettoken()
                a, z = self.parse_alt()
                aa.addarc(a)
                z.addarc(zz)
            return aa, zz

    def parse_alt(self):
        # ALT: ITEM+
        a, b = self.parse_item()
        while (self.value in ("(", "[") or
               self.type in (token.NAME, token.STRING)):
            c, d = self.parse_item()
            b.addarc(c)
            b = d
        return a, b

    def parse_item(self):
        # ITEM: '[' RHS ']' | ATOM ['+' | '*']
        if self.value == "[":
            self.gettoken()
            a, z = self.parse_rhs()
            self.expect(token.OP, "]")
            a.addarc(z)
            return a, z
        else:
            a, z = self.parse_atom()
            value = self.value
            if value not in ("+", "*"):
                return a, z
            self.gettoken()
            z.addarc(a)
            if value == "+":
                return a, z
            else:
                return a, a

    def parse_atom(self):
        # ATOM: '(' RHS ')' | NAME | STRING
        if self.value == "(":
            self.gettoken()
            a, z = self.parse_rhs()
            self.expect(token.OP, ")")
            return a, z
        elif self.type in (token.NAME, token.STRING):
            a = NFAState()
            z = NFAState()
            a.addarc(z, self.value)
            self.gettoken()
            return a, z
        else:
            self.raise_error("expected (...) or NAME or STRING, got %s/%s",
                             self.type, self.value)

    def expect(self, type, value=None):
        if self.type != type or (value is not None and self.value != value):
            self.raise_error("expected %s/%s, got %s/%s",
                             type, value, self.type, self.value)
        value = self.value
        self.gettoken()
        return value

    def gettoken(self):
        tup = next(self.lexer)
        while tup[0] in (tokenize.COMMENT, tokenize.NL):
            tup = next(self.lexer)
        self.type, self.value, self.begin, self.end, self.line = tup
        #print token.tok_name[self.type], repr(self.value)

    def raise_error(self, msg, *args):
        if args:
            msg = msg % args
        raise SyntaxError(msg, ('<grammar>', self.end[0],
                                self.end[1], self.line))

class NFAState(object):

    def __init__(self):
        self.arcs = [] # list of (label, NFAState) pairs

    def addarc(self, next, label=None):
        assert label is None or isinstance(label, str)
        assert isinstance(next, NFAState)
        self.arcs.append((label, next))

class DFAState(object):

    def __init__(self, nfaset, final):
        assert isinstance(nfaset, dict)
        assert isinstance(next(iter(nfaset)), NFAState)
        assert isinstance(final, NFAState)
        self.nfaset = nfaset
        self.isfinal = final in nfaset
        self.arcs = {} # map from label to DFAState

    def addarc(self, next, label):
        assert isinstance(label, str)
        assert label not in self.arcs
        assert isinstance(next, DFAState)
        self.arcs[label] = next

    def unifystate(self, old, new):
        for label, next in self.arcs.items():
            if next is old:
                self.arcs[label] = new

    def __eq__(self, other):
        # Equality test -- ignore the nfaset instance variable
        assert isinstance(other, DFAState)
        if self.isfinal != other.isfinal:
            return False
        # Can't just return self.arcs == other.arcs, because that
        # would invoke this method recursively, with cycles...
        if len(self.arcs) != len(other.arcs):
            return False
        for label, next in self.arcs.items():
            if next is not other.arcs.get(label):
                return False
        return True

    __hash__ = None # For Py3 compatibility.


def calcfirst(dfas, first, name):
    """Recursive function that mutates first."""
    dfa = dfas[name]
    first[name] = None # dummy to detect left recursion
    state = dfa[0]
    totalset = {}
    overlapcheck = {}
    for label, _ in state.arcs.items():
        if label in dfas:
            if label in first:
                fset = first[label]
                if fset is None:
                    raise ValueError("recursion for rule %r" % name)
            else:
                calcfirst(dfas, first, label)
                fset = first[label]
            totalset.update(fset)
            overlapcheck[label] = fset
        else:
            totalset[label] = 1
            overlapcheck[label] = {label: 1}
    inverse = {}
    for label, itsfirst in overlapcheck.items():
        for symbol in itsfirst:
            if symbol in inverse:
                raise ValueError("rule %s is ambiguous; %s is in the"
                                 " first sets of %s as well as %s" %
                                 (name, symbol, label, inverse[symbol]))
            inverse[symbol] = label
    first[name] = totalset


def make_label(tok_def, gr, label):
    """Given a grammar item, return a unique integer representing it.

    It could be:
    1. or_test      - a non-terminal
    2. Expr_Name    - a terminal
    3. 'for'        - keyword   (quotes)
    4. '>='         - operator  (quotes)

    Oil addition
    5. Op_RBracket -- anything with _ is assumed to be in the Id namespace.
    """
    #log('make_label %r', label)
    # XXX Maybe this should be a method on a subclass of converter?
    ilabel = len(gr.labels)
    if label[0].isalpha():
        if label in gr.symbol2number:  # NON-TERMINAL
            if label in gr.symbol2label:
                return gr.symbol2label[label]
            else:
                gr.labels.append(gr.symbol2number[label])
                gr.symbol2label[label] = ilabel
                return ilabel
        else:  # TERMINAL like (NAME, NUMBER, STRING)
            itoken = tok_def.GetTerminalNum(label)
            if itoken in gr.tokens:
                return gr.tokens[itoken]
            else:
                gr.labels.append(itoken)
                #log('%s %d -> %s', token.tok_name[itoken], itoken, ilabel)
                gr.tokens[itoken] = ilabel
                return ilabel
    else:
        # Either a keyword or an operator
        assert label[0] in ('"', "'"), label
        value = eval(label)

        # Treat 'xor' just like '^'.  TODO: I think this code can be
        # simplified.
        n = tok_def.GetKeywordNum(value)  # int or None

        if value[0].isalpha() and n is None:  # A word like 'for', 'xor'
            # Then look in the keywords automatically extracted from the
            # grammar.
            if value in gr.keywords:
                return gr.keywords[value]
            else:
                gr.labels.append(token.NAME)  # arbitrary number < 256
                gr.keywords[value] = ilabel
                return ilabel

        else:  # An operator e.g. '>='
            if n is None:
                itoken = tok_def.GetOpNum(value)
            else:
                itoken = n

            if itoken in gr.tokens:
                return gr.tokens[itoken]
            else:
                gr.labels.append(itoken)
                gr.tokens[itoken] = ilabel
                return ilabel


def make_first(tok_def, rawfirst, gr):
    first = {}
    for label in sorted(rawfirst):
        ilabel = make_label(tok_def, gr, label)
        ##assert ilabel not in first # XXX failed on <> ... !=
        first[ilabel] = 1
    return first


def MakeGrammar(f, tok_def=None):
  """Construct a Grammar object from a file."""

  lexer = tokenize.generate_tokens(f.readline)
  p = ParserGenerator(lexer)
  dfas, startsymbol = p.parse()

  first = {}  # map from symbol name to set of tokens
  for name in sorted(dfas):
    if name not in first:
      calcfirst(dfas, first, name)
      #print name, self.first[name].keys()

  # TODO: startsymbol support could be removed.  The call to p.setup() in
  # PushTokens() can always specify it explicitly.
  names = sorted(dfas)
  names.remove(startsymbol)
  names.insert(0, startsymbol)

  gr = grammar.Grammar()
  for name in names:
      i = 256 + len(gr.symbol2number)
      gr.symbol2number[name] = i
      gr.number2symbol[i] = name

  tok_def = tok_def or PythonTokDef()
  for name in names:
      dfa = dfas[name]
      states = []
      for state in dfa:
          arcs = []
          for label, next_ in sorted(state.arcs.items()):
              arcs.append((make_label(tok_def, gr, label), dfa.index(next_)))
          if state.isfinal:
              arcs.append((0, dfa.index(state)))
          states.append(arcs)
      gr.states.append(states)
      fi = make_first(tok_def, first[name], gr)
      gr.dfas[gr.symbol2number[name]] = (states, fi)

  gr.start = gr.symbol2number[startsymbol]
  return gr

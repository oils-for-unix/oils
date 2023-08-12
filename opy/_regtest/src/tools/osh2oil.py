from __future__ import print_function
"""
fix.py -- Do source transformations.  Somewhat like 'go fix'.

TODO: Change := to =, and var/const/set
"""

import sys

from asdl import const
from core import util
from core import word
from osh.meta import ast, Id

from _devbuild.gen import runtime_asdl

word_style_e = runtime_asdl.word_style_e

log = util.log

command_e = ast.command_e
redir_e = ast.redir_e
word_e = ast.word_e
word_part_e = ast.word_part_e
arith_expr_e = ast.arith_expr_e
bool_expr_e = ast.bool_expr_e
lhs_expr_e = ast.lhs_expr_e


class Cursor(object):
  """
  Wrapper for printing/transforming a complete source file stored in a single
  arena.
  """
  def __init__(self, arena, f):
    self.arena = arena
    self.f = f
    self.next_span_id = 0

  def PrintUntil(self, until_span_id):
    # Sometimes we add +1
    assert until_span_id < const.NO_INTEGER, 'Missing span ID, got %d' % until_span_id
    #log('PrintUntil %d', until_span_id)
    for span_id in range(self.next_span_id, until_span_id):
      #log('Looking up span id %d', span_id)
      span = self.arena.GetLineSpan(span_id)
      #log('SPAN %s', span)

      line = self.arena.GetLine(span.line_id)
      piece = line[span.col : span.col + span.length]
      self.f.write(piece)
      # Spacing
      #self.f.write('%r' % piece)
    #self.f.write('__')

    self.next_span_id = until_span_id

  def SkipUntil(self, next_span_id):
    """Skip everything before next_span_id.
    Printing will start at next_span_id
    """
    assert next_span_id != const.NO_INTEGER, next_span_id
    self.next_span_id = next_span_id


def PrintAsOil(arena, node, debug_spans):
  #print node
  #print(spans)
  if debug_spans:
    for i, span in enumerate(arena.spans):
      line = arena.GetLine(span.line_id)
      piece = line[span.col : span.col + span.length]
      print('%5d %r' % (i, piece), file=sys.stderr)
    print('(%d spans)' % len(arena.spans), file=sys.stderr)

  cursor = Cursor(arena, sys.stdout)
  fixer = OilPrinter(cursor, arena, sys.stdout)
  fixer.DoCommand(node, None, at_top_level=True)  # no local symbols yet
  fixer.End()


    # Cases:
    #
    # - Does it look like $foo?
    #   - Pedantic mode, then:
    #     x = @split(foo)          No globbing here!
    #                              @split($1) or @1 ?
    #     @-foo @-1 in expression mode
    #     And then for command mode, you will have *@1 and *@foo.  Split first
    #     then glob.
    #
    #   - Nice mode, then foo
    #     --assume no-word-splitting
    # - Does it look like $(( 1 + 2 )) ?  or $(echo hi)
    #   pedantic mode:  $(1 + 2) or @[echo hi]   ?
    #   nice mode: $(1 + 2) or $[echo hi]
    #
    # - Does it look like "$foo" or "${foo:-}"?  Then it's just x = foo
    #   x = foo or 'default'
    # - Does it contain any substitutions?  Then whole thing is double quoted
    # - Otherwise single quoted
    #
    # PROBLEM: ~ substitution.  That is disabled by "".
    # You can turn it into $HOME I guess
    # const foo = $HOME/hello
    # const foo = $~/bar  # hm I kind of don't like this but OK
    # const foo = "$~/bar"
    # const foo = [ ~/bar ][0]  # does this make sense?
    # const foo = `~/bar`

    # I think ~ should be like $ -- special.  Maybe even inside double quotes?
    # Or only at the front?


# QEFS is wrong?  Because RHS never gets split!  It can always be foo=$1/foo.
# Not used because RHS not split:
# $x -> @-x  and  ${x} -> @-x
# ${x:-default}  ->  @-(x or 'default')

def _GetRhsStyle(w):
  # NOTE: Pattern matching style would be a lot nicer for this...

  # Arith and command sub both retain $() and $[], so they are not pure
  # "expressions".
  VAR_SUBS = (word_part_e.SimpleVarSub, word_part_e.BracedVarSub,
              word_part_e.TildeSubPart)
  OTHER_SUBS = (word_part_e.CommandSubPart, word_part_e.ArithSubPart)

  ALL_SUBS = VAR_SUBS + OTHER_SUBS

  # Actually splitting NEVER HAPPENS ON ASSIGNMENT.  LEAVE IT OFF.

  if len(w.parts) == 0:
    raise AssertionError(w)

  elif len(w.parts) == 1:
    part0 = w.parts[0]
    if part0.tag in VAR_SUBS:
      # $x -> x  and  ${x} -> x  and ${x:-default} -> x or 'default'
      # ~ -> homedir()
      # ~andy -> homedir('andy')
      # tilde()
      # tilde('andy') ?
      return word_style_e.Expr
    elif part0.tag in OTHER_SUBS:
      return word_style_e.Unquoted

    elif part0.tag == word_part_e.DoubleQuotedPart:
      if len(part0.parts) == 1:
        dq_part0 = part0.parts[0]
        # "$x" -> x  and  "${x}" -> x  and "${x:-default}" -> x or 'default'
        if dq_part0.tag in VAR_SUBS:
          return word_style_e.Expr
        elif dq_part0.tag in OTHER_SUBS:
          return word_style_e.Unquoted

  # Tilde subs also cause double quoted style.
  for part in w.parts:
    if part.tag == word_part_e.DoubleQuotedPart:
      for dq_part in part.parts:
        if dq_part.tag in ALL_SUBS:
          return word_style_e.DQ
    elif part.tag in ALL_SUBS:
      return word_style_e.DQ

  return word_style_e.SQ


# TODO: Change to --assume, and have a default for each one?
#
# NICE mode: Assume that the user isn't relying on word splitting.  A lot of
# users want this!
#
# Problem cases:
#
# for name in $(find ...); do echo $name; done
#
# This doesn't split.  Heuristic:
#
# This should be a bunch of flags:
#
# --assume 'no-word-splitting no-undefined' etc.
#   globals-defined-first-outside-func (then we can generated := vs. ::=)
# --split-output-from-commands 'find ls'  # tokenize these

# Special case: "find" is assumed to produce multiple things that you will want
# to split?  But that doesn't go within function calls.  Hm.
#
# $(find -type f) -> @[find -type f]

NICE = 0

# Try to convert with pedantic correctness.  Not sure if users will want this
# though.  Most people are not super principled about their shell programs.
# But experts might want it.  Experts might want to run ShellCheck first and
# quote everything, and then everything will be unquoted.
#
# "$foo" "${foo}" -> $foo $foo
# $foo -> @-foo   -> split then glob?
#         *@foo    maybe
# $(find -type f) -> @[find -type f]

PEDANTIC = 1


class OilPrinter(object):
  """
  Convert osh code to oil.

  - command invocations
    - find invocations
    - xargs
  """
  def __init__(self, cursor, arena, f, mode=NICE):
    self.cursor = cursor
    self.arena = arena
    self.f = f
    # In PEDANTIC mode, we translate unquoted $foo to @-foo, which means it will
    # be split and globbed?
    self.mode = mode

  def _DebugSpid(self, spid):
    span = self.arena.GetLineSpan(spid)
    line = self.arena.GetLine(span.line_id)
    # TODO: This should be factored out
    s = line[span.col : span.col + span.length]
    print('SPID %d = %r' % (spid, s), file=sys.stderr)

  def End(self):
    """Make sure we print until the end of the file."""
    end_id = len(self.arena.spans)
    self.cursor.PrintUntil(end_id)

  def DoRedirect(self, node, local_symbols):
    #print(node, file=sys.stderr)
    self.cursor.PrintUntil(node.spids[0])

    # TODO:
    # - Do < and <& the same way.
    # - How to handle here docs and here docs?
    # - >> becomes >+ or >-, or maybe >>>

    if node.tag == redir_e.Redir:
      if node.fd == const.NO_INTEGER:
        if node.op_id == Id.Redir_Great:
          self.f.write('>')  # Allow us to replace the operator
          self.cursor.SkipUntil(node.spids[0] + 1)
        elif node.op_id == Id.Redir_GreatAnd:
          self.f.write('> !')  # Replace >& 2 with > !2
          spid = word.LeftMostSpanForWord(node.arg_word)
          self.cursor.SkipUntil(spid)
          #self.DoWordInCommand(node.arg_word)

      else:
        # NOTE: Spacing like !2>err.txt vs !2 > err.txt can be done in the
        # formatter.
        self.f.write('!%d ' % node.fd)
        if node.op_id == Id.Redir_Great:
          self.f.write('>')
          self.cursor.SkipUntil(node.spids[0] + 1)
        elif node.op_id == Id.Redir_GreatAnd:
          self.f.write('> !')  # Replace 1>& 2 with !1 > !2
          spid = word.LeftMostSpanForWord(node.arg_word)
          self.cursor.SkipUntil(spid)

      self.DoWordInCommand(node.arg_word, local_symbols)

    elif node.tag == redir_e.HereDoc:
      # TODO:
      # If do_expansion, then """, else '''
      # HereDoc LST node needs spids for both opening and closing delimiter.
      raise NotImplementedError(node.__class__.__name__)

    else:
      raise AssertionError(node.__class__.__name__)

    # <<< 'here word'
    # << 'here word'
    #
    # 2> out.txt
    # !2 > out.txt

    # cat 1<< EOF
    # hello $name
    # EOF
    # cat !1 << """
    # hello $name
    # """
    #
    # cat << 'EOF'
    # no expansion
    # EOF
    #   cat <<- 'EOF'
    #   no expansion and indented
    #
    # cat << '''
    # no expansion
    # '''
    #   cat << '''
    #   no expansion and indented
    #   '''

    # Warn about multiple here docs on a line.
    # As an obscure feature, allow
    # cat << \'ONE' << \"TWO"
    # 123
    # ONE
    # 234
    # TWO
    # The _ is an indicator that it's not a string to be piped in.
    pass

  def DoAssignment(self, node, at_top_level, local_symbols):
    """
    local_symbols:
      - Add every 'local' declaration to it
        - problem: what if you have local in an "if" ?
        - we could treat it like nested scope and see what happens?  Do any
          programs have a problem with it?
          case/if/for/while/BraceGroup all define scopes or what?
          You don't want inconsistency of variables that could be defined at
          any point.
          - or maybe you only need it within "if / case" ?  Well I guess
            for/while can break out of the loop and cause problems.  A break is
              an "if".

      - for subsequent
    """
    # Change RHS to expression language.  Bare words not allowed.  foo -> 'foo'

    has_rhs = False  # TODO: This is on a per-variable basis.
                     # local foo -> var foo = ''
                     # readonly foo -> setconst foo
                     # export foo -> export foo

    # TODO:
    # - This depends on self.mode.
    # - And we also need the enclosing FuncDef node to analyze.
    #   - or we need a symbol table for the current function.  Forget about
    #
    # Oil keywords:
    # - global : scope qualifier
    # - var, const : mutability
    # - setconst, export : state mutation
    #
    # Operators:
    # = and :=
    #
    # NOTE: Bash also has "unset".  Does anyone use it?
    # You can use "delete" like Python I guess.  It's not the opposite of
    # set.

    # NOTE:
    # - We CAN tell if a variable has been defined locally.
    # - We CANNOT tell if it's been defined globally, because different files
    # share the same global namespace, and we can't statically figure out what
    # files are in the program.
    defined_locally = False  # is it a local variable in this function?
                             # can't tell if global
    # We can change it from = to := or ::= (in pedantic mode)
    new_assign_op_e = None

    if node.keyword == Id.Assign_Local:
      # Assume that 'local' it's a declaration.  In osh, it's an error if
      # locals are redefined.  In bash, it's OK to do 'local f=1; local f=2'.
      # Could have a flag if enough people do this.
      if at_top_level:
        raise RuntimeError('local at top level is invalid')

      if defined_locally:
        raise RuntimeError("Can't redefine local")

      keyword_spid = node.spids[0]
      self.cursor.PrintUntil(keyword_spid)
      self.cursor.SkipUntil(keyword_spid + 1)
      self.f.write('var')

      if local_symbols is not None:
        for pair in node.pairs:
          # NOTE: Not handling local a[b]=c
          if pair.lhs.tag == lhs_expr_e.LhsName:
            #print("REGISTERED %s" % pair.lhs.name)
            local_symbols[pair.lhs.name] = True

    elif node.keyword == Id.Assign_None:
      self.cursor.PrintUntil(node.spids[0])

      # For now, just detect whether the FIRST assignment on the line has been
      # declared locally.  We might want to split every line into separate
      # statements.
      if local_symbols is not None:
        lhs0 = node.pairs[0].lhs
        if lhs0.tag == lhs_expr_e.LhsName and lhs0.name in local_symbols:
          defined_locally = True
        #print("CHECKING NAME", lhs0.name, defined_locally, local_symbols)

      # need semantic analysis.
      # Would be nice to assume that it's a local though.
      if at_top_level:
        self.f.write('global ')  # can't be redefined
        new_assign_op_e = '::='
        #self.f.write('global TODO := TODO')  # mutate global or define it
      elif defined_locally:
        new_assign_op_e = ':='  # assume mutation of local
        #self.f.write('[local mutated]')
      else:
        # we're in a function, but it's not defined locally.
        self.f.write('global ')  # assume mutation of local
        if self.mode == PEDANTIC:  # assume globals defined
          new_assign_op_e = '::='
        else:
          new_assign_op_e = ':='

    elif node.keyword == Id.Assign_Readonly:
      # Explicit const.  Assume it can't be redefined.
      # Verb.
      #
      # Top level;
      #   readonly FOO=bar  -> const FOO = 'bar'
      #   readonly FOO -> freeze FOO
      # function level:
      #   readonly FOO=bar  -> const global FOO ::= 'bar'
      #   readonly FOO  -> freeze FOO
      keyword_spid = node.spids[0]
      if at_top_level:
        self.cursor.PrintUntil(keyword_spid)
        self.cursor.SkipUntil(keyword_spid + 1)
        self.f.write('const')  # can't be redefined
      elif defined_locally:
        self.f.write('setconst FOO = "bar"')
      else:
        self.f.write('setconst global FOO = "bar"')

    elif node.keyword == Id.Assign_Declare:
      # declare -rx foo spam=eggs
      # export foo
      # setconst foo
      #
      # spam = eggs
      # export spam

      # Have to parse the flags
      self.f.write('TODO ')

    # foo=bar spam=eggs -> foo = 'bar', spam = 'eggs'
    n = len(node.pairs)
    for i, pair in enumerate(node.pairs):
      assert pair.lhs.tag == lhs_expr_e.LhsName

      left_spid = pair.spids[0]
      self.cursor.PrintUntil(left_spid)
      # Assume skipping over one Lit_VarLike token
      self.cursor.SkipUntil(left_spid + 1)

      # Replace name.  I guess it's Lit_Chars.
      self.f.write(pair.lhs.name)
      op = new_assign_op_e if new_assign_op_e else '='
      self.f.write(' %s ' % op)

      # foo=bar -> foo = 'bar'
      #print('RHS', pair.rhs, file=sys.stderr)
      if pair.rhs is None:
        self.f.write("''")  # local i -> var i = ''
      else:
        self.DoWordAsExpr(pair.rhs, local_symbols)

      if i != n - 1:
        self.f.write(',')

  def DoCommand(self, node, local_symbols, at_top_level=False):
    if node.tag == command_e.CommandList:
      # TODO: How to distinguish between echo hi; echo bye; and on separate
      # lines
      for child in node.children:
        self.DoCommand(child, local_symbols)

    elif node.tag == command_e.SimpleCommand:
      # How to preserve spaces between words?  Do you want to do it?
      # Well you need to test this:
      #
      # echo foo \
      #   bar

      # TODO: Need to print until the left most part of the phrase?  the phrase
      # is a word, binding, redirect.
      #self.cursor.PrintUntil()

      if node.more_env:
        (left_spid,) = node.more_env[0].spids
        self.cursor.PrintUntil(left_spid)
        self.f.write('env ')

        # We only need to transform the right side, not left side.
        for pair in node.more_env:
          self.DoWordInCommand(pair.val, local_symbols)

      # More translations:
      # - . to source
      # - eval to sh-eval

      if node.words:
        first_word = node.words[0]
        ok, val, quoted = word.StaticEval(first_word)
        word0_spid = word.LeftMostSpanForWord(first_word)
        if ok and not quoted:
          if val == '[':
            last_word = node.words[-1]
            # Check if last word is ]
            ok, val, quoted = word.StaticEval(last_word)
            if ok and not quoted and val == ']':
              # Replace [ with 'test'
              self.cursor.PrintUntil(word0_spid)
              self.cursor.SkipUntil(word0_spid + 1)
              self.f.write('test')

              for w in node.words[1:-1]:
                self.DoWordInCommand(w, local_symbols)

              # Now omit ]
              last_spid = word.LeftMostSpanForWord(last_word)
              self.cursor.PrintUntil(last_spid - 1)  # Get the space before
              self.cursor.SkipUntil(last_spid + 1)  # ] takes one spid
              return
            else:
              raise RuntimeError('Got [ without ]')

          elif val == '.':
            self.cursor.PrintUntil(word0_spid)
            self.cursor.SkipUntil(word0_spid + 1)
            self.f.write('source')
            return

      for w in node.words:
        self.DoWordInCommand(w, local_symbols)

      # NOTE: This will change to "phrase"?  Word or redirect.
      for r in node.redirects:
        self.DoRedirect(r, local_symbols)

      # TODO: Print the terminator.  Could be \n or ;
      # Need to print env like PYTHONPATH = 'foo' && ls
      # Need to print redirects:
      # < > are the same.  << is here string, and >> is assignment.
      # append is >+

      # TODO: static_eval of simple command
      # - [ -> "test".  Eliminate trailing ].
      # - . -> source, etc.

    elif node.tag == command_e.Assignment:
      self.DoAssignment(node, at_top_level, local_symbols)

    elif node.tag == command_e.Pipeline:
      # Obscure: |& turns into |- or |+ for stderr.
      # TODO:
      # if ! true; then -> if not true {

      # if ! echo | grep; then -> if not { echo | grep } {
      # }
      # not is like do {}, but it negates the return value I guess.

      for child in node.children:
        self.DoCommand(child, local_symbols)

    elif node.tag == command_e.AndOr:
      for child in node.children:
        self.DoCommand(child, local_symbols)

    elif node.tag == command_e.Sentence:
      # 'ls &' to 'fork ls'
      # Keep ; the same.
      self.DoCommand(node.child, local_symbols)

    # This has to be different in the function case.
    elif node.tag == command_e.BraceGroup:
      # { echo hi; } -> do { echo hi }
      # For now it might be OK to keep 'do { echo hi; }
      #left_spid, right_spid = node.spids
      (left_spid,) = node.spids

      self.cursor.PrintUntil(left_spid)
      self.cursor.SkipUntil(left_spid + 1)
      self.f.write('do {')

      for child in node.children:
        self.DoCommand(child, local_symbols)

    elif node.tag == command_e.Subshell:
      # (echo hi) -> shell echo hi
      # (echo hi; echo bye) -> shell {echo hi; echo bye}

      (left_spid, right_spid) = node.spids

      self.cursor.PrintUntil(left_spid)
      self.cursor.SkipUntil(left_spid + 1)
      self.f.write('shell {')

      self.DoCommand(node.child, local_symbols)

      #self._DebugSpid(right_spid)
      #self._DebugSpid(right_spid + 1)

      #print('RIGHT SPID', right_spid)
      self.cursor.PrintUntil(right_spid)
      self.cursor.SkipUntil(right_spid + 1)
      self.f.write('}')

    elif node.tag == command_e.DParen:
      # Just change (( )) to ( )
      # Test it with while loop
      self.DoArithExpr(node.child, local_symbols)

    elif node.tag == command_e.DBracket:
      # [[ 1 -eq 2 ]] to (1 == 2)
      self.DoBoolExpr(node.expr)

    elif node.tag == command_e.FuncDef:
      # TODO: skip name
      #self.f.write('proc %s' % node.name)

      # New symbol table for every function.
      new_local_symbols = {}

      # Should be the left most span, including 'function'
      self.cursor.PrintUntil(node.spids[0])

      self.f.write('proc ')
      self.f.write(node.name)
      self.cursor.SkipUntil(node.spids[1])

      if node.body.tag == command_e.BraceGroup:
        # Don't add "do" like a standalone brace group.  Just use {}.
        for child in node.body.children:
          self.DoCommand(child, new_local_symbols)
      else:
        pass
        # Add {}.
        # proc foo {
        #   shell {echo hi; echo bye}
        # }
        #self.DoCommand(node.body)

    elif node.tag == command_e.BraceGroup:
      for child in node.children:
        self.DoCommand(child, local_symbols)

    elif node.tag == command_e.DoGroup:
      do_spid, done_spid = node.spids
      self.cursor.PrintUntil(do_spid)
      self.cursor.SkipUntil(do_spid + 1)
      self.f.write('{')

      for child in node.children:
        self.DoCommand(child, local_symbols)

      self.cursor.PrintUntil(done_spid)
      self.cursor.SkipUntil(done_spid + 1)
      self.f.write('}')

    elif node.tag == command_e.ForEach:
      # Need to preserve spaces between words, because there can be line
      # wrapping.
      # for x in a b c \
      #    d e f; do

      in_spid, semi_spid = node.spids

      if in_spid == const.NO_INTEGER:
        #self.cursor.PrintUntil()  # 'for x' and then space
        self.f.write('for %s in @Argv ' % node.iter_name)
        self.cursor.SkipUntil(node.body.spids[0])
      else:
        self.cursor.PrintUntil(in_spid + 1)  # 'for x in' and then space
        self.f.write('[')
        for w in node.iter_words:
          self.DoWordInCommand(w, local_symbols)
        self.f.write(']')
        #print("SKIPPING SEMI %d" % semi_spid, file=sys.stderr)

      if semi_spid != const.NO_INTEGER:
        self.cursor.PrintUntil(semi_spid)
        self.cursor.SkipUntil(semi_spid + 1)

      self.DoCommand(node.body, local_symbols)

    elif node.tag == command_e.ForExpr:
      # Change (( )) to ( ), and then _FixDoGroup
      pass

    elif node.tag == command_e.While:
      cond = node.cond
      if len(cond) == 1 and cond[0].tag == command_e.Sentence:
        spid = cond[0].terminator.span_id
        self.cursor.PrintUntil(spid)
        self.cursor.SkipUntil(spid + 1)

      self.DoCommand(node.body, local_symbols)

    elif node.tag == command_e.If:
      else_spid, fi_spid = node.spids

      # if foo; then -> if foo {
      # elif foo; then -> } elif foo {
      for arm in node.arms:
        elif_spid, then_spid = arm.spids
        if elif_spid != const.NO_INTEGER:
          self.cursor.PrintUntil(elif_spid)
          self.f.write('} ')

        cond = arm.cond
        if len(cond) == 1 and cond[0].tag == command_e.Sentence:
          sentence = cond[0]
          self.DoCommand(sentence, local_symbols)

          # Remove semi-colon
          semi_spid = sentence.terminator.span_id
          self.cursor.PrintUntil(semi_spid)
          self.cursor.SkipUntil(semi_spid + 1)
        else:
          for child in arm.cond:
            self.DoCommand(child, local_symbols)

        self.cursor.PrintUntil(then_spid)
        self.cursor.SkipUntil(then_spid + 1)
        self.f.write('{')

        for child in arm.action:
          self.DoCommand(child, local_symbols)

      # else -> } else {
      if node.else_action:
        self.cursor.PrintUntil(else_spid)
        self.f.write('} ')
        self.cursor.PrintUntil(else_spid + 1)
        self.f.write(' {')

        for child in node.else_action:
          self.DoCommand(child, local_symbols)

      # fi -> }
      self.cursor.PrintUntil(fi_spid)
      self.cursor.SkipUntil(fi_spid + 1)
      self.f.write('}')

    elif node.tag == command_e.Case:
      case_spid, in_spid, esac_spid = node.spids
      self.cursor.PrintUntil(case_spid)
      self.cursor.SkipUntil(case_spid + 1)
      self.f.write('matchstr')

      # Reformat "$1" to $1
      self.DoWordInCommand(node.to_match, local_symbols)

      self.cursor.PrintUntil(in_spid)
      self.cursor.SkipUntil(in_spid + 1)
      self.f.write('{')  # matchstr $var {

      # each arm needs the ) and the ;; node to skip over?
      for arm in node.arms:
        left_spid, rparen_spid, dsemi_spid, last_spid = arm.spids
        #print(left_spid, rparen_spid, dsemi_spid)

        self.cursor.PrintUntil(left_spid)
        # Hm maybe keep | because it's semi-deprecated?  You can use
        # reload|force-reload {
        # }
        # e/reload|force-reload/ {
        # }
        # / 'reload' or 'force-reload' / {
        # }
        #
        # Yeah it's the more abbreviated syntax.

        # change | to 'or'
        for pat in arm.pat_list:
          pass

        # Skip this
        self.cursor.PrintUntil(rparen_spid)
        self.cursor.SkipUntil(rparen_spid + 1)
        self.f.write(' {')  # surround it with { }

        for child in arm.action:
          self.DoCommand(child, local_symbols)

        if dsemi_spid != const.NO_INTEGER:
          self.cursor.PrintUntil(dsemi_spid)
          self.cursor.SkipUntil(dsemi_spid + 1)
          # NOTE: indentation here will be off because ;; is likely indented
          # with body.
          self.f.write('}')
        elif last_spid != const.NO_INTEGER:
          self.cursor.PrintUntil(last_spid)
          # NOTE: Indentation is also off here.  Arbitrarily put 4 spaces.
          self.f.write('    }\n')
        else:
          raise AssertionError(
              "Expected with dsemi_spid or last_spid in case arm")

      self.cursor.PrintUntil(esac_spid)
      self.cursor.SkipUntil(esac_spid + 1)
      self.f.write('}')  # strmatch $var {

    elif node.tag == command_e.NoOp:
      pass

    elif node.tag == command_e.ControlFlow:
      # No change for break / return / continue
      pass

    elif node.tag == command_e.TimeBlock:
      self.DoCommand(node.pipeline, local_symbols)

    else:
      #log('Command not handled: %s', node)
      raise AssertionError(node.__class__.__name__)

  def DoWordAsExpr(self, node, local_symbols):
    style = _GetRhsStyle(node)
    if style == word_style_e.SQ:
      self.f.write("'")
      self.DoWordInCommand(node, local_symbols)
      self.f.write("'")
    elif style == word_style_e.DQ:
      self.f.write('"')
      self.DoWordInCommand(node, local_symbols)
      self.f.write('"')
    else:
      # "${foo:-default}" -> foo or 'default'
      # ${foo:-default} -> @split(foo or 'default')
      #                    @(foo or 'default')  -- implicit split.

      if word.IsVarSub(node):  # ${1} or "$1"
        # Do it in expression mode
        pass
      # NOTE: ArithSub with $(1 +2 ) is different than 1 + 2 because of
      # conversion to string.

      # For now, just stub it out
      self.DoWordInCommand(node, local_symbols)

  def DoWordInCommand(self, node, local_symbols):
    """
    New reserved symbols:
      echo == must be changed to echo '==' because = is a reserved symbol.
      echo @$foo -> echo "@$foo" because @ is reserved

    Problems:
    rm --verbose=true
    rm '--verbose=true'  -- is this bad?

    Same with comma
    foo, bar = 1

    # I guess we can allow this
    ls --long foo,bar

    or force:
    (foo, bar) = 1

    Maybe we need a clever 'pre-lex'
    overwhelmingly the second char will be ' '

    foo/bar/foo.py
    foo.py
    ./hello
    foo_bar
    [a-zA-Z0-9]  / - . _  -- filename chars


    first word:
      var, const, export, setconst, global
      func, proc, do, not, shell,
      maybe: time, coproc, etc.

      =    -- generic expression, = 1+2

    non-filename char AFTER first word
      cmd:
          ' '     foo bar baz
          '\n'    foo
          '<'     foo < bar
          '>'     foo > bar
          !       ls !2 > !1
          |       who | wc -l
          |-       who |- wc -l

      expr:
          =   foo = bar
          ,   a, b = x
          [   a[x] = 1
          (   f(x)  for(  while(  if(

    1+2  -- I think this tries to run the command
    """
    # Are we getting rid of word joining?  Or maybe keep it but discourage and
    # provide alternatives.
    #
    # You don't really have a problem with byte strings, those are b'foo', but
    # that's in expression mode, not command mode.

    # Problems:
    # - Tilde sub can't be quoted.  ls ~/foo/"foo" are incompatible with the
    # rule.
    # - Globs can't be quoted. ls 'foo'*.py can't be ls "foo*.py" -- it means
    # something different.
    # Might need to finish more of the globber to figure this out.

    # What about here docs words?  It's a double quoted part, but with
    # different formatting!
    if node.tag == word_e.CompoundWord:

      # UNQUOTE simple var subs

      # TODO: I think we have to print the beginning and the end?

      #left_spid = word.LeftMostSpanForWord(node)
      #right_spid = word.RightMostSpanForWord(node)
      #right_spid = -1
      #print('DoWordInCommand %s %s' % (left_spid, right_spid), file=sys.stderr)

      # Special case for "$@".  Wow this needs pattern matching!
      # TODO:
      # "$foo" -> $foo
      # "${foo}" -> $foo

      if (len(node.parts) == 1 and
          node.parts[0].tag == word_part_e.DoubleQuotedPart):
        dq_part = node.parts[0]

        # TODO: Double quoted part needs left and right IDs
        left_spid, right_spid = dq_part.spids
        assert right_spid != const.NO_INTEGER, right_spid

        if len(dq_part.parts) == 1:
          part0 = dq_part.parts[0]
          if part0.tag == word_part_e.SimpleVarSub:
            vsub_part = dq_part.parts[0]
            if vsub_part.token.id == Id.VSub_At:
              # NOTE: This is off for double quoted part.  Hack to subtract 1.
              self.cursor.PrintUntil(left_spid)
              self.cursor.SkipUntil(right_spid + 1)  # " then $@ then "
              self.f.write('@Argv')
              return  # Done replacing

            # "$1" -> $1, "$foo" -> $foo
            if vsub_part.token.id in (Id.VSub_Number, Id.VSub_Name):
              self.cursor.PrintUntil(left_spid)
              self.cursor.SkipUntil(right_spid + 1)
              self.f.write(vsub_part.token.val)
              return

          # Single arith sub, command sub, etc.
          # On the other hand, an unquoted one needs to turn into
          #
          # $(echo one two) -> @[echo one two]
          # `echo one two` -> @[echo one two]
          #
          # ${var:-'the default'} -> @$(var or 'the default')
          #
          # $((1 + 2)) -> $(1 + 2) -- this is OK unquoted

          elif part0.tag == word_part_e.BracedVarSub:
            # Skip over quote
            self.cursor.PrintUntil(left_spid)
            self.cursor.SkipUntil(left_spid + 1)
            self.DoWordPart(part0, local_symbols)
            self.cursor.SkipUntil(right_spid + 1)
            return

          elif part0.tag == word_part_e.CommandSubPart:
            self.cursor.PrintUntil(left_spid)
            self.cursor.SkipUntil(left_spid + 1)
            self.DoWordPart(part0, local_symbols)
            self.cursor.SkipUntil(right_spid + 1)
            return

      # It's None for here docs I think.
      #log("NODE %s", node)
      #if left_spid is not None and left_spid >= 0:
        #span = self.arena.GetLineSpan(span_id)
        #print(span)

        #self.cursor.PrintUntil(left_spid)
        #pass

      # TODO: 'foo'"bar" should be "foobar", etc.
      # If any part is double quoted, you can always double quote the whole
      # thing?
      for part in node.parts:
        self.DoWordPart(part, local_symbols)

      #if right_spid >= 0:
        #self.cursor.PrintUntil(right_spid)
        #pass

    else:
      raise AssertionError(node.__class__.__name__)

  def DoWordPart(self, node, local_symbols, quoted=False):
    span_id = word.LeftMostSpanForPart(node)
    if span_id is not None and span_id != const.NO_INTEGER:
      span = self.arena.GetLineSpan(span_id)
      #print(span)

      self.cursor.PrintUntil(span_id)

    if node.tag == word_part_e.ArrayLiteralPart:
      pass

    elif node.tag == word_part_e.EscapedLiteralPart:
      if quoted:
        pass
      else:
        # If unquoted \e, it should quoted instead.  ' ' vs. \<invisible space>
        # Hm is this necessary though?  I think the only motivation is changing
        # \{ and \( for macros.  And ' ' to be readable/visible.
        t = node.token
        val = t.val[1:]
        assert len(val) == 1, val
        if val != '\n':
          self.cursor.PrintUntil(t.span_id)
          self.cursor.SkipUntil(t.span_id + 1)
          self.f.write("'%s'" % val)

    elif node.tag == word_part_e.LiteralPart:
      # Print it literally.
      # TODO: We might want to do it all on the word level though.  For
      # example, foo"bar" becomes "foobar" in oil.
      spid = node.token.span_id
      if spid is None:
        #raise RuntimeError('%s has no span_id' % node.token)
        # TODO: Fix word.TildeDetect to construct proper tokens.
        print('WARNING:%s has no span_id' % node.token, file=sys.stderr)
      else:
        self.cursor.PrintUntil(spid + 1)

    elif node.tag == word_part_e.TildeSubPart:  # No change
      pass

    elif node.tag == word_part_e.SingleQuotedPart:
      # TODO:
      # '\n' is '\\n'
      # $'\n' is '\n'
      # TODO: Should print until right_spid
      # left_spid, right_spid = node.spids
      if node.tokens:  # Empty string has no tokens
        last_spid = node.tokens[-1].span_id
        self.cursor.PrintUntil(last_spid + 1)

    elif node.tag == word_part_e.DoubleQuotedPart:
      for part in node.parts:
        self.DoWordPart(part, local_symbols, quoted=True)

    elif node.tag == word_part_e.SimpleVarSub:
      spid = node.token.span_id
      op_id = node.token.id

      if op_id == Id.VSub_Name:
        self.cursor.PrintUntil(spid + 1)

      elif op_id == Id.VSub_Number:
        self.cursor.PrintUntil(spid + 1)

      elif op_id == Id.VSub_Bang:  # $!
        self.f.write('$BgPid')  # Job most recently placed in background
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_At:  # $@
        self.f.write('$ifsjoin(Argv)')
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Pound:  # $#
        self.f.write('$Argc')
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Dollar:  # $$
        self.f.write('$Pid')
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Star:  # $*
        # PEDANTIC: Depends if quoted or unquoted
        self.f.write('$ifsjoin(Argv)')
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Hyphen:  # $*
        self.f.write('$Flags')
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_QMark:  # $?
        self.f.write('$Status')
        self.cursor.SkipUntil(spid + 1)

      else:
        raise AssertionError(op_id)

    elif node.tag == word_part_e.BracedVarSub:
      left_spid, right_spid = node.spids

      # NOTE: Why do we need this but we don't need it in command sub?
      self.cursor.PrintUntil(left_spid)

      name_spid = node.token.span_id
      op_id = node.token.id

      parens_needed = True
      if node.bracket_op:
        # a[1]
        # These two change the sigil!  ${a[@]} is now @a!
        # a[@]
        # a[*]
        pass

      if node.prefix_op:
        # len()
        pass
      if node.suffix_op:
        # foo.trimLeft()
        # foo.trimGlobLeft()
        # foo.trimGlobLeft(longest=True)
        #
        # python lstrip() does something different

        # a[1:1]

        # .replace()
        # .replaceGlob()

        pass

      if op_id == Id.VSub_QMark:
        self.cursor.PrintUntil(name_spid + 1)

      if parens_needed:
        # Skip over left bracket and write our own.
        self.f.write('$(')
        self.cursor.SkipUntil(left_spid + 1)

        # Placeholder for now
        self.cursor.PrintUntil(right_spid)

        # Skip over right bracket and write our own.
        self.f.write(')')
      else:
        pass

      self.cursor.SkipUntil(right_spid + 1)

    elif node.tag == word_part_e.CommandSubPart:
      left_spid, right_spid = node.spids

      #self.cursor.PrintUntil(left_spid)
      self.f.write('$[')
      self.cursor.SkipUntil(left_spid + 1)

      self.DoCommand(node.command_list, local_symbols)

      self.f.write(']')
      self.cursor.SkipUntil(right_spid + 1)
      # change to $[echo hi]

    elif node.tag == word_part_e.ArithSubPart:
      left_spid, right_spid = node.spids

      # Skip over left bracket and write our own.
      self.f.write('$(')
      self.cursor.SkipUntil(left_spid + 1)

      # NOTE: This doesn't do anything yet.
      self.DoArithExpr(node.anode, local_symbols)
      # Placeholder for now
      self.cursor.PrintUntil(right_spid - 1)

      # Skip over right bracket and write our own.
      self.f.write(')')
      self.cursor.SkipUntil(right_spid + 1)

    else:
      raise AssertionError(node.__class__.__name__)

  def DoArithExpr(self, node, local_symbols):
    if node.tag == arith_expr_e.ArithBinary:
      # Maybe I should just write the left span and right span for each word?
      #self.f.write(str(node.left))

      if node.op_id == Id.Arith_Plus:
        # NOTE: Right isn't necessarily a word!
        r_id = word.LeftMostSpanForWord(node.right.w)
        #self.cursor.SkipUntil(r_id)
        #self.f.write('PLUS')

      #self.f.write(str(node.right))
    elif node.tag == arith_expr_e.ArithWord:
      self.DoWordInCommand(node.w, local_symbols)

    else:
      raise AssertionError(node.__class__.__name__)

  def DoBoolExpr(self, node):
    # TODO: switch on node.tag
    pass

# WordPart?

# array_item
#
# These get turned into expressions
#
# bracket_op
# suffix_op
# prefix_op

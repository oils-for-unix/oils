from __future__ import print_function
"""
osh2oil.py: Translate OSH to Oil.
"""

import sys

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import word_style_e
from _devbuild.gen.syntax_asdl import (
    command_e, redir_e, word_e, word_part_e, sh_lhs_expr_e
)
from asdl import runtime
from core import util

from osh import word_

log = util.log
p_die = util.p_die


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
    if until_span_id == runtime.NO_SPID:
      assert 0, 'Missing span ID, got %d' % until_span_id

    for span_id in xrange(self.next_span_id, until_span_id):
      span = self.arena.GetLineSpan(span_id)

      # A span for Eof may have a line_id of -1 when the file is completely
      # empty.
      if span.line_id == -1:
        continue

      line = self.arena.GetLine(span.line_id)
      piece = line[span.col : span.col + span.length]
      self.f.write(piece)

    self.next_span_id = until_span_id

  def SkipUntil(self, next_span_id):
    """Skip everything before next_span_id.
    Printing will start at next_span_id
    """
    if (next_span_id == runtime.NO_SPID or
        next_span_id == runtime.NO_SPID + 1):
      assert 0, 'Missing span ID, got %d' % next_span_id
    self.next_span_id = next_span_id


def PrintArena(arena):
  """For testing the invariant that the spans "add up" to the original doc."""
  cursor = Cursor(arena, sys.stdout)
  cursor.PrintUntil(arena.LastSpanId())


def PrintSpans(arena):
  """Just to see spans."""
  if len(arena.spans) == 1:  # Special case for line_id == -1
    print('Empty file with EOF span on invalid line:')
    print('%s' % arena.spans[0])
    return

  for i, span in enumerate(arena.spans):
    line = arena.GetLine(span.line_id)
    piece = line[span.col : span.col + span.length]
    print('%5d %r' % (i, piece))
  print('(%d spans)' % len(arena.spans), file=sys.stderr)


def PrintAsOil(arena, node):
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
  """
  Determine what style an assignment should use. '' or "", or an expression.

  SQ      foo=         setglobal foo = ''
  SQ      foo=''       setglobal foo = ''
  DQ      foo=""       setglobal foo = ""  # Or we could normalize it if no subs?
  DQ      foo=""       setglobal foo = ""  # Or we could normalize it if no subs?

  # Need these too.
  # Or honestly should C strings be the default?  And then raw strings are
  # optional?  Because most usages of \n and \0 can turn into Oil?
  # Yeah I want the default to be statically parseable, so we subvert the \t
  # and \n of command line tools?
  # As long as we are fully analyzing the strings, we might as well go all the
  # way!
  # I think I need a PartialStaticEval() to paper over this.
  #
  # The main issue is regex and globs, because they use escape for a different
  # purpose.  I think just do
  # grep r'foo\tbar' or something.

  C_SQ    foo=$'\n'          setglobal foo = C'\n'
  C_DQ    foo=$'\n'"$bar"    setglobal foo = C"\n$(bar)"

  Expr    path=${1:-}             setglobal path = $1 or ''
  Expr    host=${2:-$(hostname)}  setglobal host = $2 or $[hostname]

  What's the difference between Expr and Unquoted?  I think they're the same/
  """

  # NOTE: Pattern matching style would be a lot nicer for this...

  # Arith and command sub both retain $() and $[], so they are not pure
  # "expressions".
  VAR_SUBS = (word_part_e.SimpleVarSub, word_part_e.BracedVarSub,
              word_part_e.TildeSub)
  OTHER_SUBS = (word_part_e.CommandSub, word_part_e.ArithSub)

  ALL_SUBS = VAR_SUBS + OTHER_SUBS

  # Actually splitting NEVER HAPPENS ON ASSIGNMENT.  LEAVE IT OFF.

  if w.tag == word_e.Empty:
    return word_style_e.SQ

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

    elif part0.tag == word_part_e.DoubleQuoted:
      if len(part0.parts) == 1:
        dq_part0 = part0.parts[0]
        # "$x" -> x  and  "${x}" -> x  and "${x:-default}" -> x or 'default'
        if dq_part0.tag in VAR_SUBS:
          return word_style_e.Expr
        elif dq_part0.tag in OTHER_SUBS:
          return word_style_e.Unquoted

  # Tilde subs also cause double quoted style.
  for part in w.parts:
    if part.tag == word_part_e.DoubleQuoted:
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
    self.cursor.PrintUntil(self.arena.LastSpanId())

  def DoRedirect(self, node, local_symbols):
    #print(node, file=sys.stderr)
    op_spid = node.op.span_id
    op_id = node.op.id
    self.cursor.PrintUntil(op_spid)

    # TODO:
    # - Do < and <& the same way.
    # - How to handle here docs and here docs?
    # - >> becomes >+ or >-, or maybe >>>

    if node.tag == redir_e.Redir:
      if node.fd == runtime.NO_SPID:
        if op_id == Id.Redir_Great:
          self.f.write('>')  # Allow us to replace the operator
          self.cursor.SkipUntil(op_spid + 1)
        elif op_id == Id.Redir_GreatAnd:
          self.f.write('> !')  # Replace >& 2 with > !2
          spid = word_.LeftMostSpanForWord(node.arg_word)
          self.cursor.SkipUntil(spid)
          #self.DoWordInCommand(node.arg_word)

      else:
        # NOTE: Spacing like !2>err.txt vs !2 > err.txt can be done in the
        # formatter.
        self.f.write('!%d ' % node.fd)
        if op_id == Id.Redir_Great:
          self.f.write('>')
          self.cursor.SkipUntil(op_spid + 1)
        elif op_id == Id.Redir_GreatAnd:
          self.f.write('> !')  # Replace 1>& 2 with !1 > !2
          spid = word_.LeftMostSpanForWord(node.arg_word)
          self.cursor.SkipUntil(spid)

      self.DoWordInCommand(node.arg_word, local_symbols)

    elif node.tag == redir_e.HereDoc:
      ok, delimiter, delim_quoted = word_.StaticEval(node.here_begin)
      if not ok:
        p_die('Invalid here doc delimiter', word=node.here_begin)

      # Turn everything into <<.  We just change the quotes
      self.f.write('<<')

      #here_begin_spid2 = word_.RightMostSpanForWord(node.here_begin)
      if delim_quoted:
        self.f.write(" '''")
      else:
        self.f.write(' """')

      delim_end_spid = word_.RightMostSpanForWord(node.here_begin)
      self.cursor.SkipUntil(delim_end_spid + 1)

      #self.cursor.SkipUntil(here_begin_spid + 1)

      # Now print the lines.  TODO: Have a flag to indent these to the level of
      # the owning command, e.g.
      #   cat <<EOF
      # EOF
      # Or since most here docs are the top level, you could just have a hack
      # for a fixed indent?  TODO: Look at real use cases.
      for part in node.stdin_parts:
        self.DoWordPart(part, local_symbols)

      self.cursor.SkipUntil(node.here_end_span_id + 1)
      if delim_quoted:
        self.f.write("'''\n")
      else:
        self.f.write('"""\n')

      # Need
      #self.cursor.SkipUntil(here_end_spid2)

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

  def DoShAssignment(self, node, at_top_level, local_symbols):
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
    # - And we also need the enclosing ShFunction node to analyze.
    #   - or we need a symbol table for the current function.  Forget about
    #
    # Oil keywords:
    # - global : scope qualifier
    # - var, const : mutability
    # - export : state mutation
    # - setconst -- make a variable mutable.  or maybe freeze var?
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

    # DISABLED after doing dynamic assignments.  We could reconstruct these
    # from SimpleCommand?  Look at argv[0] and then do static parsing to
    # assign_pair?

    if 0:
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
          if pair.lhs.tag == sh_lhs_expr_e.Name:
            #print("REGISTERED %s" % pair.lhs.name)
            local_symbols[pair.lhs.name] = True

    elif 1:
      self.cursor.PrintUntil(node.spids[0])

      # For now, just detect whether the FIRST assignment on the line has been
      # declared locally.  We might want to split every line into separate
      # statements.
      if local_symbols is not None:
        lhs0 = node.pairs[0].lhs
        if lhs0.tag == sh_lhs_expr_e.Name and lhs0.name in local_symbols:
          defined_locally = True
        #print("CHECKING NAME", lhs0.name, defined_locally, local_symbols)

      has_array = any(
          pair.lhs.tag == sh_lhs_expr_e.UnparsedIndex for pair in node.pairs)

      # need semantic analysis.
      # Would be nice to assume that it's a local though.
      if has_array:
        self.f.write('compat ')  # 'compat array-assign' syntax
      elif at_top_level:
        self.f.write('setglobal ')
      elif defined_locally:
        self.f.write('set ')
        #self.f.write('[local mutated]')
      else:
        # We're in a function, but it's not defined locally, so we must be
        # mutatting a global.
        self.f.write('setglobal ')

    elif 0:
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
        self.f.write('const')
      elif defined_locally:
        # TODO: Actually we might want 'freeze here.  In bash, you can make a
        # variable readonly after its defined.
        raise RuntimeError("Constant redefined locally")
      else:
        # Same as global level
        self.cursor.PrintUntil(keyword_spid)
        self.cursor.SkipUntil(keyword_spid + 1)
        self.f.write('const')

    elif 0:
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
      if pair.lhs.tag == sh_lhs_expr_e.Name:
        left_spid = pair.spids[0]
        self.cursor.PrintUntil(left_spid)
        # Assume skipping over one Lit_VarLike token
        self.cursor.SkipUntil(left_spid + 1)

        # Replace name.  I guess it's Lit_Chars.
        self.f.write(pair.lhs.name)
        self.f.write(' = ')

        # TODO: This should be translated from Empty.
        if pair.rhs.tag == word_e.Empty:
          self.f.write("''")  # local i -> var i = ''
        else:
          self.DoWordAsExpr(pair.rhs, local_symbols)

      elif pair.lhs.tag == sh_lhs_expr_e.UnparsedIndex:
        # NOTES:
        # - parse_ctx.one_pass_parse should be on, so the span invariant
        #   is accurate
        # - Then do the following translation:
        #   a[x+1]="foo $bar" ->
        #   compat array-assign a 'x+1' "$foo $bar"
        # This avoids dealing with nested arenas.
        #
        # TODO: This isn't great when there are multiple assignments.
        #   a[x++]=1 b[y++]=2
        #
        # 'compat' could apply to the WHOLE statement, with multiple
        # assignments.
        self.f.write("array-assign %s '%s' " % (pair.lhs.name, pair.lhs.index))

        if pair.rhs.tag == word_e.Empty:
          self.f.write("''")  # local i -> var i = ''
        else:
          rhs_spid = word_.LeftMostSpanForWord(pair.rhs)
          self.cursor.SkipUntil(rhs_spid)
          self.DoWordAsExpr(pair.rhs, local_symbols)

      else: 
        raise AssertionError(pair.lhs.__class__.__name__)

      if i != n - 1:
        self.f.write(',')

  def DoCommand(self, node, local_symbols, at_top_level=False):
    if node.tag == command_e.CommandList:
      # TODO: How to distinguish between echo hi; echo bye; and on separate
      # lines
      for child in node.children:
        self.DoCommand(child, local_symbols, at_top_level=at_top_level)

    elif node.tag == command_e.Simple:
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
        ok, val, quoted = word_.StaticEval(first_word)
        word0_spid = word_.LeftMostSpanForWord(first_word)
        if ok and not quoted:
          if val == '[':
            last_word = node.words[-1]
            # Check if last word is ]
            ok, val, quoted = word_.StaticEval(last_word)
            if ok and not quoted and val == ']':
              # Replace [ with 'test'
              self.cursor.PrintUntil(word0_spid)
              self.cursor.SkipUntil(word0_spid + 1)
              self.f.write('test')

              for w in node.words[1:-1]:
                self.DoWordInCommand(w, local_symbols)

              # Now omit ]
              last_spid = word_.LeftMostSpanForWord(last_word)
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

    elif node.tag == command_e.ShAssignment:
      self.DoShAssignment(node, at_top_level, local_symbols)

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

      self.DoCommand(node.command_list, local_symbols)

      #self._DebugSpid(right_spid)
      #self._DebugSpid(right_spid + 1)

      #print('RIGHT SPID', right_spid)
      self.cursor.PrintUntil(right_spid)
      self.cursor.SkipUntil(right_spid + 1)
      self.f.write('}')

    elif node.tag == command_e.DParen:
      # (( a == 0 )) is sh-expr ' a == 0 '
      #
      # NOTE: (( n++ )) is auto-translated to sh-expr 'n++', but could be set
      # n++.
      left_spid, right_spid = node.spids
      self.cursor.PrintUntil(left_spid)
      self.cursor.SkipUntil(left_spid + 1)
      self.f.write("sh-expr '")
      self.cursor.PrintUntil(right_spid - 1)  # before ))
      self.cursor.SkipUntil(right_spid + 1)  # after )) -- each one is a token
      self.f.write("'")

    elif node.tag == command_e.DBracket:
      # [[ 1 -eq 2 ]] to (1 == 2)
      self.DoBoolExpr(node.expr)

    elif node.tag == command_e.ShFunction:
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

      _, in_spid, semi_spid = node.spids

      if in_spid == runtime.NO_SPID:
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

      if semi_spid != runtime.NO_SPID:
        self.cursor.PrintUntil(semi_spid)
        self.cursor.SkipUntil(semi_spid + 1)

      self.DoCommand(node.body, local_symbols)

    elif node.tag == command_e.ForExpr:
      # Change (( )) to ( ), and then _FixDoGroup
      pass

    elif node.tag == command_e.WhileUntil:

      # Skip 'until', and replace it with 'while not'
      if node.keyword.id == Id.KW_Until:
        kw_spid = node.keyword.span_id
        self.cursor.PrintUntil(kw_spid)
        self.f.write('while not')
        self.cursor.SkipUntil(kw_spid + 1)

      cond = node.cond
      # Skip the semi-colon in the condition, which is ususally a Sentence
      if len(cond) == 1 and cond[0].tag == command_e.Sentence:
        self.DoCommand(cond[0].child, local_symbols)
        semi_spid = cond[0].terminator.span_id
        self.cursor.SkipUntil(semi_spid + 1)

      self.DoCommand(node.body, local_symbols)

    elif node.tag == command_e.If:
      else_spid, fi_spid = node.spids

      # if foo; then -> if foo {
      # elif foo; then -> } elif foo {
      for i, arm in enumerate(node.arms):
        elif_spid, then_spid = arm.spids
        if i != 0:  # 'if' not 'elif' on the first arm
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
      self.f.write('match')

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
        # Hm maybe keep | because it's semi-deprecated?  You acn use
        # reload|force-relaod {
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

        self.f.write('with ')
        # Remove the )
        self.cursor.PrintUntil(rparen_spid)
        self.cursor.SkipUntil(rparen_spid + 1)

        for child in arm.action:
          self.DoCommand(child, local_symbols)

        if dsemi_spid != runtime.NO_SPID:
          # Remove ;;
          self.cursor.PrintUntil(dsemi_spid)
          self.cursor.SkipUntil(dsemi_spid + 1)
        elif last_spid != runtime.NO_SPID:
          self.cursor.PrintUntil(last_spid)
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
    # TODO: This is wrong!
    style = _GetRhsStyle(node)
    if style == word_style_e.SQ:
      self.f.write("'")
      self.DoWordInCommand(node, local_symbols)
      self.f.write("'")
    elif style == word_style_e.DQ:
      self.f.write('"')
      self.DoWordInCommand(node, local_symbols)
      self.f.write('"')
    # TODO: Put these back
    #elif style == word_style_e.Expr:
    #  pass
    #elif style == word_style_e.Unquoted:
    #  pass
    else:
      # "${foo:-default}" -> foo or 'default'
      # ${foo:-default} -> @split(foo or 'default')
      #                    @(foo or 'default')  -- implicit split.

      if word_.IsVarSub(node):  # ${1} or "$1"
        # Do it in expression mode
        pass
      # NOTE: ArithSub with $(1 +2 ) is different than 1 + 2 because of
      # conversion to string.

      # For now, jsut stub it out
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
    if node.tag == word_e.Compound:

      # UNQUOTE simple var subs

      # TODO: I think we have to print the beginning and the end?

      #left_spid = word_.LeftMostSpanForWord(node)
      #right_spid = word_.RightMostSpanForWord(node)
      #right_spid = -1
      #print('DoWordInCommand %s %s' % (left_spid, right_spid), file=sys.stderr)

      # Special case for "$@".  Wow this needs pattern matching!
      # TODO:
      # "$foo" -> $foo
      # "${foo}" -> $foo

      if (len(node.parts) == 1 and
          node.parts[0].tag == word_part_e.DoubleQuoted):
        dq_part = node.parts[0]

        # NOTE: In double quoted case, this is the begin and end quote.
        # Do we need a HereDoc part?

        left_spid, right_spid = dq_part.spids
        # This is not set in the case of here docs?  Why not?
        #assert left_spid != runtime.NO_SPID, left_spid
        assert right_spid != runtime.NO_SPID, right_spid

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
            if vsub_part.token.id in (Id.VSub_Number, Id.VSub_DollarName):
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

          elif part0.tag == word_part_e.CommandSub:
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

    elif node.tag == word_e.BracedTree:
      # Not doing anything now
      pass

    elif node.tag == word_e.Empty:
      # Hm do I need to make it ''?
      # This only happens for:
      # s=
      # a[x]=
      # ${x:-}
      pass

    else:
      raise AssertionError(node.__class__.__name__)

  def DoWordPart(self, node, local_symbols, quoted=False):
    span_id = word_.LeftMostSpanForPart(node)
    if span_id is not None and span_id != runtime.NO_SPID:
      span = self.arena.GetLineSpan(span_id)

      self.cursor.PrintUntil(span_id)

    if node.tag == word_part_e.ShArrayLiteral:
      pass

    elif node.tag == word_part_e.AssocArrayLiteral:
      pass

    elif node.tag == word_part_e.EscapedLiteral:
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

    elif node.tag == word_part_e.Literal:
      # Print it literally.
      # TODO: We might want to do it all on the word level though.  For
      # example, foo"bar" becomes "foobar" in oil.
      spid = node.span_id
      if spid == runtime.NO_SPID:
        #raise RuntimeError('%s has no span_id' % node.token)
        # TODO: Fix word_.TildeDetect to construct proper tokens.
        log('WARNING: %s has no span_id' % node)
      else:
        self.cursor.PrintUntil(spid + 1)

    elif node.tag == word_part_e.TildeSub:  # No change
      pass

    elif node.tag == word_part_e.SingleQuoted:
      # TODO:
      # '\n' is '\\n'
      # $'\n' is '\n'
      # TODO: Should print until right_spid
      # left_spid, right_spid = node.spids
      if node.tokens:  # Empty string has no tokens
        last_spid = node.tokens[-1].span_id
        self.cursor.PrintUntil(last_spid + 1)

    elif node.tag == word_part_e.DoubleQuoted:
      for part in node.parts:
        self.DoWordPart(part, local_symbols, quoted=True)

    elif node.tag == word_part_e.SimpleVarSub:
      spid = node.token.span_id
      op_id = node.token.id

      if op_id == Id.VSub_DollarName:
        self.cursor.PrintUntil(spid + 1)

      elif op_id == Id.VSub_Number:
        self.cursor.PrintUntil(spid + 1)

      elif op_id == Id.VSub_Bang:  # $!
        self.f.write('$BgPid')  # Job most recently placed in backgroudn
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

    elif node.tag == word_part_e.CommandSub:
      left_spid, right_spid = node.spids

      #self.cursor.PrintUntil(left_spid)
      self.f.write('$[')
      self.cursor.SkipUntil(left_spid + 1)

      self.DoCommand(node.command_list, local_symbols)

      self.f.write(']')
      self.cursor.SkipUntil(right_spid + 1)
      # change to $[echo hi]

    elif node.tag == word_part_e.ArithSub:
      # We're not bothering to translate the arithmetic language.
      # Just turn $(( x ? 0 : 1 )) into $shExpr('x ? 0 : 1').

      left_spid, right_spid = node.spids

      # Skip over left bracket and write our own.
      self.f.write("$shExpr('")
      self.cursor.SkipUntil(left_spid + 1)

      # NOTE: This doesn't do anything yet.
      #self.DoArithExpr(node.anode, local_symbols)
      # Placeholder for now
      self.cursor.PrintUntil(right_spid - 1)

      # Skip over right bracket and write our own.
      self.f.write("')")
      self.cursor.SkipUntil(right_spid + 1)

    elif node.tag == word_part_e.ExtGlob:
      # Change this into a function?  It depends whether it is used as
      # a glob or fnmatch.
      # 
      # Example of glob:
      # cloud/sandstorm/make-bundle.sh
      pass

    else:
      raise AssertionError(node.__class__.__name__)

  def DoBoolExpr(self, node):
    # TODO:
    # - Some are turned into '( x ~ *.py )'
    # - Some are turned into 'test x -lt y'
    pass


# WordPart?

# array_item
#
# These get turned into expressions
#
# bracket_op
# suffix_op
# prefix_op

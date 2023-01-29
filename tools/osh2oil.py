from __future__ import print_function
"""
osh2oil.py: Translate OSH to Oil.

TODO: Turn this into 2 tools.

ysh-prettify: May change the meaning of the code.  Should have a list of
selectable rules.

Files should already have shopt --set ysh:upgrade at the top

ESSENTIAL

Command:
  
  then/fi, do/done -> { }

  new case statement

  f() { } -> proc f { }  (changes scope)

  subshell -> forkwait, because () is taken
    { } to fopen { }?

  Approximate: var declaration:
    local a=b -> var a = 'b', I think

  <<EOF here docs to '''

Word:
  "$@" -> @ARGV

  Not common: unquoted $x -> @[split(x)]

LEGACY that I don't personally use

Builtins:
  [ -> test
  . -> source

Word:
  backticks -> $() (I don't use this) 
  quote removal "$foo" -> $foo
  brace removal ${foo} and "${foo}" -> $foo

TOOL ysh-format:

  fix indentation and spacing, like clang-format
"""

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import word_style_e, word_style_t
from _devbuild.gen.syntax_asdl import (
    Token, loc,
    command_e, command__ShAssignment, command__Simple, command__Sentence, 
    command__Pipeline, command__AndOr, command__DoGroup,
    command__Subshell, command__DBracket, command__DParen,
    command__ForEach, command__WhileUntil, command__If, command__Case,
    command__ShFunction, command__TimeBlock,
    command__CommandList,
    BraceGroup,

    for_iter_e, for_iter__Words,
    rhs_word_e, rhs_word_t,
    word_e, word_t,
    word_part_e, word_part_t, word_part__EscapedLiteral,
    compound_word,
    simple_var_sub, braced_var_sub, command_sub, double_quoted, single_quoted,
    sh_lhs_expr_e, sh_lhs_expr__Name,
    condition_e, condition__Shell,
    redir, redir_param_e, redir_param__HereDoc,
)
from asdl import runtime
from core.pyerror import log, p_die
from frontend import location
from osh import word_
from mycpp import mylib
from mycpp.mylib import print_stderr, tagswitch

from typing import Dict, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import command_t
  from core import alloc


class Cursor(object):
  """
  Wrapper for printing/transforming a complete source file stored in a single
  arena.
  """
  def __init__(self, arena, f):
    # type: (alloc.Arena, mylib.Writer) -> None
    self.arena = arena
    self.f = f
    self.next_span_id = 0

  def PrintUntil(self, until_span_id):
    # type: (int) -> None

    # Sometimes we add +1
    if until_span_id == runtime.NO_SPID:
      assert 0, 'Missing span ID, got %d' % until_span_id

    for span_id in xrange(self.next_span_id, until_span_id):
      span = self.arena.GetToken(span_id)

      # A span for Eof may have a line_id of -1 when the file is completely
      # empty.
      if span.line_id == -1:
        continue

      line = self.arena.GetLine(span.line_id)
      piece = line[span.col : span.col + span.length]
      self.f.write(piece)

    self.next_span_id = until_span_id

  def SkipUntil(self, next_span_id):
    # type: (int) -> None
    """Skip everything before next_span_id.
    Printing will start at next_span_id
    """
    if (next_span_id == runtime.NO_SPID or
        next_span_id == runtime.NO_SPID + 1):
      assert 0, 'Missing span ID, got %d' % next_span_id
    self.next_span_id = next_span_id


def PrintArena(arena):
  # type: (alloc.Arena) -> None
  """For testing the invariant that the spans "add up" to the original doc."""
  cursor = Cursor(arena, mylib.Stdout())
  cursor.PrintUntil(arena.LastSpanId())


def PrintSpans(arena):
  # type: (alloc.Arena) -> None
  """Just to see spans."""
  if len(arena.tokens) == 1:  # Special case for line_id == -1
    print('Empty file with EOF span on invalid line:')
    print('%s' % arena.tokens[0])
    return

  for i, span in enumerate(arena.tokens):
    line = arena.GetLine(span.line_id)
    piece = line[span.col : span.col + span.length]
    print('%5d %r' % (i, piece))
  print_stderr('(%d tokens)' % len(arena.tokens))


def PrintAsOil(arena, node):
  # type: (alloc.Arena, command_t) -> None
  cursor = Cursor(arena, mylib.Stdout())
  fixer = OilPrinter(cursor, arena, mylib.Stdout())
  fixer.DoCommand(node, None, at_top_level=True)  # no local symbols yet
  fixer.End()


# PROBLEM: ~ substitution.  That is disabled by "".
# You can turn it into $HOME I guess
# const foo = "$HOME/src"
# const foo = %( ~/src )[0]  # does this make sense?


def _GetRhsStyle(w):
  # type: (rhs_word_t) -> word_style_t
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
  # Actually splitting NEVER HAPPENS ON ASSIGNMENT.  LEAVE IT OFF.

  UP_w = w
  with tagswitch(w) as case:
    if case(rhs_word_e.Empty):
      return word_style_e.SQ

    elif case(rhs_word_e.Compound):
      w = cast(compound_word, UP_w)
      if len(w.parts) == 0:
        raise AssertionError(w)

      elif len(w.parts) == 1:
        part0 = w.parts[0]
        UP_part0 = part0
        with tagswitch(part0) as case:
          # VAR_SUBS
          if case(word_part_e.TildeSub):
            #    x=~andy/src
            # -> setvar x = homedir('andy') + '/src'
            return word_style_e.Expr

          elif case(word_part_e.Literal):
            #    local x=y
            # -> var x = 'y'
            return word_style_e.SQ

          elif case(word_part_e.SimpleVarSub):
            #    local x=$myvar
            # -> var x = "$myvar"
            # or var x = ${myvar}
            # or var x = myvar
            return word_style_e.DQ

          elif case(word_part_e.BracedVarSub, word_part_e.CommandSub,
              word_part_e.ArithSub):  
            #    x=$(hostname)
            # -> setvar x = $(hostname)
            return word_style_e.Unquoted

          elif case(word_part_e.DoubleQuoted):
            part0 = cast(double_quoted, UP_part0)

            # TODO: remove quotes in single part like "$(hostname)" -> $(hostname)
            return word_style_e.DQ

      else:
        # multiple parts use YSTR in general?
        # Depends if there are subs
        return word_style_e.DQ

  # Default
  return word_style_e.SQ


class OilPrinter(object):
  """
  Prettify OSH to YSH.
  """
  def __init__(self, cursor, arena, f):
    # type: (Cursor, alloc.Arena, mylib.Writer) -> None
    self.cursor = cursor
    self.arena = arena
    self.f = f

  def _DebugSpid(self, spid):
    # type: (int) -> None
    span = self.arena.GetToken(spid)
    line = self.arena.GetLine(span.line_id)
    # TODO: This should be factored out
    s = line[span.col : span.col + span.length]
    print_stderr('SPID %d = %r' % (spid, s))

  def End(self):
    # type: () -> None
    """Make sure we print until the end of the file."""
    self.cursor.PrintUntil(self.arena.LastSpanId())

  def DoRedirect(self, node, local_symbols):
    # type: (redir, Dict[str, bool]) -> None
    """
    Currently Unused
    TODO: It would be nice to change here docs to <<< '''
    """
    #print(node, file=sys.stderr)
    op_spid = node.op.span_id
    op_id = node.op.id
    self.cursor.PrintUntil(op_spid)

    if node.arg.tag_() == redir_param_e.HereDoc:
      here_doc = cast(redir_param__HereDoc, node.arg)

      here_begin = here_doc.here_begin
      ok, delimiter, delim_quoted = word_.StaticEval(here_begin)
      if not ok:
        p_die('Invalid here doc delimiter', loc.Word(here_begin))

      # Turn everything into <<<.  We just change the quotes
      self.f.write('<<<')

      #here_begin_spid2 = word_.RightMostSpanForWord(node.here_begin)
      if delim_quoted:
        self.f.write(" '''")
      else:
        self.f.write(' """')

      delim_end_spid = word_.RightMostSpanForWord(here_begin)
      self.cursor.SkipUntil(delim_end_spid + 1)

      #self.cursor.SkipUntil(here_begin_spid + 1)

      # Now print the lines.  TODO: Have a flag to indent these to the level of
      # the owning command, e.g.
      #   cat <<EOF
      # EOF
      # Or since most here docs are the top level, you could just have a hack
      # for a fixed indent?  TODO: Look at real use cases.
      for part in here_doc.stdin_parts:
        self.DoWordPart(part, local_symbols)

      self.cursor.SkipUntil(here_doc.here_end_span_id + 1)
      if delim_quoted:
        self.f.write("'''\n")
      else:
        self.f.write('"""\n')

      # Need
      #self.cursor.SkipUntil(here_end_spid2)

    else:
      raise AssertionError(node.__class__.__name__)

    # cat << EOF
    # hello $name
    # EOF
    # cat <<< """
    # hello $name
    # """

    # cat << 'EOF'
    # no expansion
    # EOF

    # cat <<< '''
    # no expansion
    # '''

  def DoShAssignment(self, node, at_top_level, local_symbols):
    # type: (command__ShAssignment, bool, Dict[str, bool]) -> None
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

    has_rhs = False  # TODO: Should be on a per-variable basis.
                     # local a=b c=d, or just punt on those
    defined_locally = False  # is it a local variable in this function?
                             # can't tell if global

    if True:
      self.cursor.PrintUntil(node.spids[0])

      # For now, just detect whether the FIRST assignment on the line has been
      # declared locally.  We might want to split every line into separate
      # statements.
      if local_symbols is not None:
        lhs0 = node.pairs[0].lhs
        #if lhs0.tag_() == sh_lhs_expr_e.Name and lhs0.name in local_symbols:
        #  defined_locally = True

        #print("CHECKING NAME", lhs0.name, defined_locally, local_symbols)

      # TODO: Avoid translating these
      has_array_index = [pair.lhs.tag_() == sh_lhs_expr_e.UnparsedIndex for pair in node.pairs]

      # need semantic analysis.
      # Would be nice to assume that it's a local though.
      if at_top_level:
        self.f.write('setvar ')
      elif defined_locally:
        self.f.write('set ')
        #self.f.write('[local mutated]')
      else:
        # We're in a function, but it's not defined locally, so we must be
        # mutating a global.
        self.f.write('setvar ')

    # foo=bar spam=eggs -> foo = 'bar', spam = 'eggs'
    n = len(node.pairs)
    for i, pair in enumerate(node.pairs):
      lhs = pair.lhs
      UP_lhs = lhs
      with tagswitch(lhs) as case:
        if case(sh_lhs_expr_e.Name):
          lhs = cast(sh_lhs_expr__Name, UP_lhs)

          left_spid = pair.spids[0]
          self.cursor.PrintUntil(left_spid)
          # Assume skipping over one Lit_VarLike token
          self.cursor.SkipUntil(left_spid + 1)

          # Replace name.  I guess it's Lit_Chars.
          self.f.write(lhs.name)
          self.f.write(' = ')

          # TODO: This should be translated from Empty.
          if pair.rhs.tag_() == rhs_word_e.Empty:
            self.f.write("''")  # local i -> var i = ''
          else:
            self.DoRhsWord(pair.rhs, local_symbols)

        else: 
          raise AssertionError(pair.lhs.__class__.__name__)

      if i != n - 1:
        self.f.write(',')

  def DoCommand(self, node, local_symbols, at_top_level=False):
    # type: (command_t, Dict[str, bool], bool) -> None

    UP_node = node

    with tagswitch(node) as case:
      if case(command_e.CommandList):
        node = cast(command__CommandList, UP_node)

        # TODO: How to distinguish between echo hi; echo bye; and on separate
        # lines
        for child in node.children:
          self.DoCommand(child, local_symbols, at_top_level=at_top_level)

      elif case(command_e.Simple):
        node = cast(command__Simple, UP_node)

        # How to preserve spaces between words?  Do you want to do it?
        # Well you need to test this:
        #
        # echo foo \
        #   bar

        if len(node.more_env):
          # We only need to transform the right side, not left side.
          for pair in node.more_env:
            self.DoRhsWord(pair.val, local_symbols)

        if len(node.words):
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

        # It would be nice to convert here docs to multi-line strings
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

      elif case(command_e.ShAssignment):
        node = cast(command__ShAssignment, UP_node)

        self.DoShAssignment(node, at_top_level, local_symbols)

      elif case(command_e.Pipeline):
        node = cast(command__Pipeline, UP_node)

        for child in node.children:
          self.DoCommand(child, local_symbols)

      elif case(command_e.AndOr):
        node = cast(command__AndOr, UP_node)

        for child in node.children:
          self.DoCommand(child, local_symbols)

      elif case(command_e.Sentence):
        node = cast(command__Sentence, UP_node)

        # 'ls &' to 'fork ls'
        # Keep ; the same.
        self.DoCommand(node.child, local_symbols)

      # This has to be different in the function case.
      elif case(command_e.BraceGroup):
        node = cast(BraceGroup, UP_node)

        # { echo hi; } -> do { echo hi }
        # For now it might be OK to keep 'do { echo hi; }
        left_spid = node.left.span_id

        self.cursor.PrintUntil(left_spid)
        self.cursor.SkipUntil(left_spid + 1)
        self.f.write('do {')

        for child in node.children:
          self.DoCommand(child, local_symbols)

      elif case(command_e.Subshell):
        node = cast(command__Subshell, UP_node)

        # (echo hi) -> shell echo hi
        # (echo hi; echo bye) -> shell {echo hi; echo bye}

        left_spid = node.spids[0]
        right_spid = node.spids[1]

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

      elif case(command_e.ShFunction):
        node = cast(command__ShFunction, UP_node)

        # TODO: skip name
        #self.f.write('proc %s' % node.name)

        # New symbol table for every function.
        new_local_symbols = {}  # type: Dict[str, bool]

        # Should be the left most span, including 'function'
        self.cursor.PrintUntil(node.spids[0])

        self.f.write('proc ')
        self.f.write(node.name)
        self.cursor.SkipUntil(node.spids[2])

        if node.body.tag_() == command_e.BraceGroup:
          # Don't add "do" like a standalone brace group.  Just use {}.
          for child in cast(BraceGroup, node.body).children:
            self.DoCommand(child, new_local_symbols)
        else:
          pass
          # Add {}.
          # proc foo {
          #   shell {echo hi; echo bye}
          # }
          #self.DoCommand(node.body)

      elif case(command_e.DoGroup):
        node = cast(command__DoGroup, UP_node)

        do_spid = node.spids[0]
        done_spid = node.spids[1]

        self.cursor.PrintUntil(do_spid)
        self.cursor.SkipUntil(do_spid + 1)
        self.f.write('{')

        for child in node.children:
          self.DoCommand(child, local_symbols)

        self.cursor.PrintUntil(done_spid)
        self.cursor.SkipUntil(done_spid + 1)
        self.f.write('}')

      elif case(command_e.ForEach):
        node = cast(command__ForEach, UP_node)

        # Need to preserve spaces between words, because there can be line
        # wrapping.
        # for x in a b c \
        #    d e f; do

        in_spid = node.spids[1]
        semi_spid = node.spids[2]

        UP_iterable = node.iterable
        with tagswitch(node.iterable) as case:
          if case(for_iter_e.Args):
            #self.cursor.PrintUntil()  # 'for x' and then space
            self.f.write('for %s in @ARGV ' % node.iter_names[0])

            # note: command_t doesn't have .spids
            self.cursor.SkipUntil(location.SpanForCommand(node.body))

          elif case(for_iter_e.Words):
            iterable = cast(for_iter__Words, UP_iterable)

            self.cursor.PrintUntil(in_spid + 2)  # 'for x in ' and then space
            self.f.write('[')
            for w in iterable.words:
              self.DoWordInCommand(w, local_symbols)
            self.f.write(']')
            #print("SKIPPING SEMI %d" % semi_spid, file=sys.stderr)

          elif case(for_iter_e.Oil):
            pass

        if semi_spid != runtime.NO_SPID:
          self.cursor.PrintUntil(semi_spid)
          self.cursor.SkipUntil(semi_spid + 1)

        self.DoCommand(node.body, local_symbols)

      elif case(command_e.WhileUntil):
        node = cast(command__WhileUntil, UP_node)

        # Skip 'until', and replace it with 'while not'
        if node.keyword.id == Id.KW_Until:
          kw_spid = node.keyword.span_id
          self.cursor.PrintUntil(kw_spid)
          self.f.write('while not')
          self.cursor.SkipUntil(kw_spid + 1)

        if node.cond.tag_() == condition_e.Shell:
          commands = cast(condition__Shell, node.cond).commands
          # Skip the semi-colon in the condition, which is ususally a Sentence
          if len(commands) == 1 and commands[0].tag_() == command_e.Sentence:
            sentence = cast(command__Sentence, commands[0])
            self.DoCommand(sentence.child, local_symbols)
            semi_spid = sentence.terminator.span_id
            self.cursor.SkipUntil(semi_spid + 1)

        self.DoCommand(node.body, local_symbols)

      elif case(command_e.If):
        node = cast(command__If, UP_node)

        else_spid = node.spids[0]
        fi_spid = node.spids[1]

        # if foo; then -> if foo {
        # elif foo; then -> } elif foo {
        for i, arm in enumerate(node.arms):
          elif_spid = arm.spids[0]
          then_spid = arm.spids[1]

          if i != 0:  # 'if' not 'elif' on the first arm
            self.cursor.PrintUntil(elif_spid)
            self.f.write('} ')

          cond = arm.cond
          if cond.tag_() == condition_e.Shell:
            commands = cast(condition__Shell, cond).commands
            if len(commands) == 1 and commands[0].tag_() == command_e.Sentence:
              sentence = cast(command__Sentence, commands[0])
              self.DoCommand(sentence, local_symbols)

              # Remove semi-colon
              semi_spid = sentence.terminator.span_id
              self.cursor.PrintUntil(semi_spid)
              self.cursor.SkipUntil(semi_spid + 1)
            else:
              for child in commands:
                self.DoCommand(child, local_symbols)

          self.cursor.PrintUntil(then_spid)
          self.cursor.SkipUntil(then_spid + 1)
          self.f.write('{')

          for child in arm.action:
            self.DoCommand(child, local_symbols)

        # else -> } else {
        if len(node.else_action):
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

      elif case(command_e.Case):
        node = cast(command__Case, UP_node)

        case_spid = node.spids[0]
        in_spid = node.spids[1]
        esac_spid = node.spids[2]

        self.cursor.PrintUntil(case_spid)
        self.cursor.SkipUntil(case_spid + 1)
        self.f.write('match')

        # Reformat "$1" to $1
        self.DoWordInCommand(node.to_match, local_symbols)

        self.cursor.PrintUntil(in_spid)
        self.cursor.SkipUntil(in_spid + 1)
        self.f.write('{')  # matchstr $var {

        # each arm needs the ) and the ;; node to skip over?
        for case_arm in node.arms:
          left_spid = case_arm.spids[0]
          rparen_spid = case_arm.spids[1]
          dsemi_spid = case_arm.spids[2]
          last_spid = case_arm.spids[3]

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
          for pat in case_arm.pat_list:
            pass

          self.f.write('with ')
          # Remove the )
          self.cursor.PrintUntil(rparen_spid)
          self.cursor.SkipUntil(rparen_spid + 1)

          for child in case_arm.action:
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

      elif case(command_e.TimeBlock):
        node = cast(command__TimeBlock, UP_node)

        self.DoCommand(node.pipeline, local_symbols)

      elif case(command_e.DParen):
        node = cast(command__DParen, UP_node)
        # TODO: arith expressions can words with command subs
        pass

      elif case(command_e.DBracket):
        node = cast(command__DBracket, UP_node)

        # TODO: bool_expr_t can have words with command subs
        pass

      else:
        pass
        #log('Command not handled: %s', node)
        #raise AssertionError(node.__class__.__name__)

  def DoRhsWord(self, node, local_symbols):
    # type: (rhs_word_t, Dict[str, bool]) -> None
    """
    For the RHS of assignments.

    TODO: for complex cases of word joining:
        local a=unquoted'single'"double"'"'

    We can try to handle it:
        var a = y"unquotedsingledouble\""

    Or simply abort and LEAVE IT ALONE.  We should only translate things we
    recognize.
    """
    UP_node = node
    with tagswitch(node) as case:
      if case(rhs_word_e.Empty):
        self.f.write("''")

      elif case(rhs_word_e.Compound):
        node = cast(compound_word, UP_node)

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
    # type: (word_t, Dict[str, bool]) -> None
    """
    e.g. remove unquoted

    echo "$x" -> echo $x

    """
    UP_node = node

    with tagswitch(node) as case:
      if case(word_e.Compound):
        node = cast(compound_word, UP_node)

        # UNQUOTE simple var subs

        # Special case for "$@".
        # TODO:
        # "$foo" -> $foo
        # "${foo}" -> $foo

        if (len(node.parts) == 1 and
            node.parts[0].tag_() == word_part_e.DoubleQuoted):
          dq_part = cast(double_quoted, node.parts[0])

          # NOTE: In double quoted case, this is the begin and end quote.
          # Do we need a HereDoc part?

          left_spid = dq_part.left.span_id
          right_spid = dq_part.right.span_id

          # This is not set in the case of here docs?  Why not?
          #assert left_spid != runtime.NO_SPID, left_spid
          assert right_spid != runtime.NO_SPID, right_spid

          if len(dq_part.parts) == 1:
            part0 = dq_part.parts[0]
            if part0.tag_() == word_part_e.SimpleVarSub:
              vsub_part = cast(simple_var_sub, dq_part.parts[0])
              if vsub_part.token.id == Id.VSub_At:
                # NOTE: This is off for double quoted part.  Hack to subtract 1.
                self.cursor.PrintUntil(left_spid)
                self.cursor.SkipUntil(right_spid + 1)  # " then $@ then "
                self.f.write('@ARGV')
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

            elif part0.tag_() == word_part_e.BracedVarSub:
              # Skip over quote
              self.cursor.PrintUntil(left_spid)
              self.cursor.SkipUntil(left_spid + 1)
              self.DoWordPart(part0, local_symbols)
              self.cursor.SkipUntil(right_spid + 1)
              return

            elif part0.tag_() == word_part_e.CommandSub:
              self.cursor.PrintUntil(left_spid)
              self.cursor.SkipUntil(left_spid + 1)
              self.DoWordPart(part0, local_symbols)
              self.cursor.SkipUntil(right_spid + 1)
              return

        # TODO: 'foo'"bar" should be "foobar", etc.
        # If any part is double quoted, you can always double quote the whole
        # thing?
        for part in node.parts:
          self.DoWordPart(part, local_symbols)

      elif case(word_e.BracedTree):
        # Not doing anything now
        pass

      else:
        raise AssertionError(node.__class__.__name__)

  def DoWordPart(self, node, local_symbols, quoted=False):
    # type: (word_part_t, Dict[str, bool], bool) -> None

    span_id = word_.LeftMostSpanForPart(node)
    if span_id != runtime.NO_SPID:
      span = self.arena.GetToken(span_id)
      self.cursor.PrintUntil(span_id)

    UP_node = node

    with tagswitch(node) as case:
      if case(word_part_e.ShArrayLiteral, word_part_e.AssocArrayLiteral,
          word_part_e.TildeSub, word_part_e.ExtGlob):
        pass

      elif case(word_part_e.EscapedLiteral):
        node = cast(word_part__EscapedLiteral, UP_node)
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

      elif case(word_part_e.Literal):
        node = cast(Token, UP_node)

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

      elif case(word_part_e.SingleQuoted):
        node = cast(single_quoted, UP_node)

        # TODO:
        # '\n' is '\\n'
        # $'\n' is '\n'
        # TODO: Should print until right_spid
        # left_spid, right_spid = node.spids
        if len(node.tokens):  # Empty string has no tokens
          last_spid = node.tokens[-1].span_id
          self.cursor.PrintUntil(last_spid + 1)

      elif case(word_part_e.DoubleQuoted):
        node = cast(double_quoted, UP_node)
        for part in node.parts:
          self.DoWordPart(part, local_symbols, quoted=True)

      elif case(word_part_e.SimpleVarSub):
        node = cast(simple_var_sub, UP_node)

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
          self.f.write('$ifsjoin(ARGV)')
          self.cursor.SkipUntil(spid + 1)

        elif op_id == Id.VSub_Pound:  # $#
          self.f.write('$Argc')
          self.cursor.SkipUntil(spid + 1)

        elif op_id == Id.VSub_Dollar:  # $$
          self.f.write('$Pid')
          self.cursor.SkipUntil(spid + 1)

        elif op_id == Id.VSub_Star:  # $*
          # PEDANTIC: Depends if quoted or unquoted
          self.f.write('$ifsjoin(ARGV)')
          self.cursor.SkipUntil(spid + 1)

        elif op_id == Id.VSub_Hyphen:  # $*
          self.f.write('$Flags')
          self.cursor.SkipUntil(spid + 1)

        elif op_id == Id.VSub_QMark:  # $?
          self.f.write('$Status')
          self.cursor.SkipUntil(spid + 1)

        else:
          pass

      elif case(word_part_e.BracedVarSub):
        node = cast(braced_var_sub, UP_node)

        left_spid = node.left.span_id
        right_spid = node.right.span_id

        # NOTE: Why do we need this but we don't need it in command sub?
        self.cursor.PrintUntil(left_spid)

        name_spid = node.token.span_id
        op_id = node.token.id

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
          pass

        if op_id == Id.VSub_QMark:
          self.cursor.PrintUntil(name_spid + 1)

        self.cursor.PrintUntil(right_spid + 1)

      elif case(word_part_e.CommandSub):
        node = cast(command_sub, UP_node)

        left_spid = node.left_token.span_id
        right_spid = node.right.span_id

        if node.left_token.id == Id.Left_Backtick:
          self.cursor.PrintUntil(left_spid)

          self.f.write('$(')
          self.cursor.SkipUntil(left_spid + 1)

          self.DoCommand(node.child, local_symbols)

          # Skip over right `
          self.cursor.SkipUntil(right_spid + 1)
          self.f.write(')')

        else:
          self.cursor.PrintUntil(right_spid + 1)

      else:
        pass

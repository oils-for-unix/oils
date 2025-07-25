# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
ui.py - User interface constructs.
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.syntax_asdl import (
    Token,
    SourceLine,
    loc,
    loc_e,
    loc_t,
    command_t,
    command_str,
    source,
    source_e,
)
from _devbuild.gen.value_asdl import value, value_e, value_t
from asdl import format as fmt
from data_lang import j8_lite
from display import pp_value
from display import pretty
from frontend import lexer
from frontend import location
from mycpp import mylib
from mycpp.mylib import print_stderr, tagswitch, log
import libc

from typing import List, Tuple, Optional, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen import arg_types
    from core import error
    from core.error import _ErrorWithLocation

_ = log


def ValType(val):
    # type: (value_t) -> str
    """For displaying type errors in the UI."""

    # TODO: consolidate these functions
    return pp_value.ValType(val)


def CommandType(cmd):
    # type: (command_t) -> str
    """For displaying commands in the UI."""

    # Displays 'Simple', 'BraceGroup', etc.
    return command_str(cmd.tag(), dot=False)


def PrettyId(id_):
    # type: (Id_t) -> str
    """For displaying type errors in the UI."""

    # Displays 'Id.BoolUnary_v' for now
    return Id_str(id_)


def PrettyToken(tok):
    # type: (Token) -> str
    """Returns a readable token value for the user.

    For syntax errors.
    """
    if tok.id == Id.Eof_Real:
        return 'EOF'

    val = tok.line.content[tok.col:tok.col + tok.length]
    # TODO: Print length 0 as 'EOF'?
    return repr(val)


def PrettyDir(dir_name, home_dir):
    # type: (str, Optional[str]) -> str
    """Maybe replace the home dir with ~.

    Used by the 'dirs' builtin and the prompt evaluator.
    """
    if home_dir is not None:
        if dir_name == home_dir or dir_name.startswith(home_dir + '/'):
            return '~' + dir_name[len(home_dir):]

    return dir_name


def PrintCaretLine(line, col, length, f):
    # type: (str, int, int, mylib.Writer) -> None
    # preserve tabs
    for c in line[:col]:
        f.write('\t' if c == '\t' else ' ')
    f.write('^')
    f.write('~' * (length - 1))
    f.write('\n')


def _PrintCodeExcerpt(line, col, length, f):
    # type: (str, int, int, mylib.Writer) -> None

    buf = mylib.BufWriter()

    # TODO: Be smart about horizontal space when printing code snippet
    # - Accept max_width param, which is terminal width or perhaps 100
    #   when there's no terminal
    # - If 'length' of token is greater than max_width, then perhaps print 10
    #   chars on each side
    # - If len(line) is less than max_width, then print everything normally
    # - If len(line) is greater than max_width, then print up to max_width
    #   but make sure to include the entire token, with some context
    #   Print > < or ... to show truncation
    #
    #   ^col 80  ^~~~~ error

    buf.write('  ')  # indent
    buf.write(line.rstrip())

    buf.write('\n  ')  # indent
    PrintCaretLine(line, col, length, buf)

    # Do this all in a single write() call so it's less likely to be
    # interleaved.  See test/runtime-errors.sh test-errexit-multiple-processes
    f.write(buf.getvalue())


def _PrintTokenTooLong(loc_tok, f):
    # type: (loc.TokenTooLong, mylib.Writer) -> None
    line = loc_tok.line
    col = loc_tok.col

    buf = mylib.BufWriter()

    buf.write('  ')
    # Only print 10 characters, since it's probably very long
    buf.write(line.content[:col + 10].rstrip())
    buf.write('\n  ')

    # preserve tabs, like _PrintCodeExcerpt
    for c in line.content[:col]:
        buf.write('\t' if c == '\t' else ' ')

    buf.write('^\n')

    source_str = GetLineSourceString(loc_tok.line, quote_filename=True)
    buf.write(
        '%s:%d: Token starting at column %d is too long: %d bytes (%s)\n' %
        (source_str, line.line_num, loc_tok.col, loc_tok.length,
         Id_str(loc_tok.id)))

    # single write() call
    f.write(buf.getvalue())


def GetFilenameString(line):
    # type: (SourceLine) -> str
    """Get the path of the file that a line appears in.

    Returns "main" if it's stdin or -c
    Returns "?" if it's not in a file.

    Used by declare -F, with shopt -s extdebug.
    """
    src = line.src
    UP_src = src

    filename_str = '?'  # default
    with tagswitch(src) as case:
        # Copying bash, it uses the string 'main'.
        # I think ? would be better here, because this can get confused with a
        # file 'main'.  But it's fine for our task file usage.
        if case(source_e.CFlag):
            filename_str = 'main'
        elif case(source_e.Stdin):
            filename_str = 'main'

        elif case(source_e.MainFile):
            src = cast(source.MainFile, UP_src)
            filename_str = src.path
        elif case(source_e.OtherFile):
            src = cast(source.OtherFile, UP_src)
            filename_str = src.path

        else:
            pass
    return filename_str


def GetLineSourceString(line, quote_filename=False):
    # type: (SourceLine, bool) -> str
    """Returns a human-readable string for dev tools.

    This function is RECURSIVE because there may be dynamic parsing.
    """
    src = line.src
    UP_src = src

    with tagswitch(src) as case:
        if case(source_e.Interactive):
            s = '[ interactive ]'  # This might need some changes
        elif case(source_e.Headless):
            s = '[ headless ]'
        elif case(source_e.CFlag):
            s = '[ -c flag ]'
        elif case(source_e.Stdin):
            src = cast(source.Stdin, UP_src)
            s = '[ stdin%s ]' % src.comment

        elif case(source_e.MainFile):
            src = cast(source.MainFile, UP_src)
            # This will quote a file called '[ -c flag ]' to disambiguate it!
            # also handles characters that are unprintable in a terminal.
            s = src.path
            if quote_filename:
                s = j8_lite.EncodeString(s, unquoted_ok=True)
        elif case(source_e.OtherFile):
            src = cast(source.OtherFile, UP_src)
            # ditto
            s = src.path
            if quote_filename:
                s = j8_lite.EncodeString(s, unquoted_ok=True)

        elif case(source_e.Dynamic):
            src = cast(source.Dynamic, UP_src)

            # Note: _PrintWithLocation() uses this more specifically

            # TODO: check loc.Missing; otherwise get Token from loc_t, then line
            blame_tok = location.TokenFor(src.location)
            if blame_tok is None:
                s = '[ %s at ? ]' % src.what
            else:
                line = blame_tok.line
                line_num = line.line_num
                outer_source = GetLineSourceString(
                    line, quote_filename=quote_filename)
                s = '[ %s at line %d of %s ]' % (src.what, line_num,
                                                 outer_source)

        elif case(source_e.Variable):
            src = cast(source.Variable, UP_src)

            if src.var_name is None:
                var_name = '?'
            else:
                var_name = repr(src.var_name)

            if src.location.tag() == loc_e.Missing:
                where = '?'
            else:
                blame_tok = location.TokenFor(src.location)
                assert blame_tok is not None
                line_num = blame_tok.line.line_num
                outer_source = GetLineSourceString(
                    blame_tok.line, quote_filename=quote_filename)
                where = 'line %d of %s' % (line_num, outer_source)

            s = '[ var %s at %s ]' % (var_name, where)

        elif case(source_e.VarRef):
            src = cast(source.VarRef, UP_src)

            orig_tok = src.orig_tok
            line_num = orig_tok.line.line_num
            outer_source = GetLineSourceString(orig_tok.line,
                                               quote_filename=quote_filename)
            where = 'line %d of %s' % (line_num, outer_source)

            var_name = lexer.TokenVal(orig_tok)
            s = '[ contents of var %r at %s ]' % (var_name, where)

        elif case(source_e.Alias):
            src = cast(source.Alias, UP_src)
            s = '[ expansion of alias %r ]' % src.argv0

        elif case(source_e.Reparsed):
            src = cast(source.Reparsed, UP_src)
            span2 = src.left_token
            outer_source = GetLineSourceString(span2.line,
                                               quote_filename=quote_filename)
            s = '[ %s in %s ]' % (src.what, outer_source)

        elif case(source_e.Synthetic):
            src = cast(source.Synthetic, UP_src)
            s = '-- %s' % src.s  # use -- to say it came from a flag

        else:
            raise AssertionError(src)

    return s


def _PrintWithLocation(prefix, msg, blame_loc, show_code):
    # type: (str, str, loc_t, bool) -> None
    """Print an error message attached to a location.

    We may quote code this:

        echo $foo
             ^~~~
        [ -c flag ]:1: Failed

    Should we have multiple locations?

    - single line and verbose?
    - and turn on "stack" tracing?  For 'source' and more?
    """
    f = mylib.Stderr()
    if blame_loc.tag() == loc_e.TokenTooLong:
        # test/spec.sh parse-errors shows this
        _PrintTokenTooLong(cast(loc.TokenTooLong, blame_loc), f)
        return

    blame_tok = location.TokenFor(blame_loc)
    # lexer.DummyToken() gives you a Lit_Chars Token with no line
    if blame_tok is None or blame_tok.line is None:
        f.write('[??? no location ???] %s%s\n' % (prefix, msg))
        return

    orig_col = blame_tok.col
    src = blame_tok.line.src
    line = blame_tok.line.content
    line_num = blame_tok.line.line_num  # overwritten by source.Reparsed case

    if show_code:
        UP_src = src

        with tagswitch(src) as case:
            if case(source_e.Reparsed):
                # Special case for LValue/backticks

                # We want the excerpt to look like this:
                #   a[x+]=1
                #       ^
                # Rather than quoting the internal buffer:
                #   x+
                #     ^

                # Show errors:
                #   test/parse-errors.sh text-arith-context

                src = cast(source.Reparsed, UP_src)
                tok2 = src.left_token
                line_num = tok2.line.line_num

                line2 = tok2.line.content
                lbracket_col = tok2.col + tok2.length
                # NOTE: The inner line number is always 1 because of reparsing.
                # We overwrite it with the original token.
                _PrintCodeExcerpt(line2, orig_col + lbracket_col, 1, f)

            elif case(source_e.Dynamic):
                src = cast(source.Dynamic, UP_src)
                # Special case for eval, unset, printf -v, etc.

                # Show errors:
                #   test/runtime-errors.sh test-assoc-array

                #print('OUTER blame_loc', blame_loc)
                #print('OUTER tok', blame_tok)
                #print('INNER src.location', src.location)

                # Print code and location for MOST SPECIFIC location
                _PrintCodeExcerpt(line, blame_tok.col, blame_tok.length, f)
                source_str = GetLineSourceString(blame_tok.line,
                                                 quote_filename=True)
                f.write('%s:%d\n' % (source_str, line_num))
                f.write('\n')

                # Recursive call: Print OUTER location, with error message
                _PrintWithLocation(prefix, msg, src.location, show_code)
                return

            else:
                _PrintCodeExcerpt(line, blame_tok.col, blame_tok.length, f)

    source_str = GetLineSourceString(blame_tok.line, quote_filename=True)

    # TODO: If the line is blank, it would be nice to print the last non-blank
    # line too?
    f.write('%s:%d: %s%s\n' % (source_str, line_num, prefix, msg))


def CodeExcerptAndPrefix(blame_tok):
    # type: (Token) -> Tuple[str, str]
    """Return a string that quotes code, and a string location prefix.

    Similar logic as _PrintWithLocation, except we know we have a token.
    """
    line = blame_tok.line

    buf = mylib.BufWriter()
    _PrintCodeExcerpt(line.content, blame_tok.col, blame_tok.length, buf)

    source_str = GetLineSourceString(line, quote_filename=True)
    prefix = '%s:%d: ' % (source_str, blame_tok.line.line_num)

    return buf.getvalue(), prefix


class ctx_Location(object):

    def __init__(self, errfmt, location):
        # type: (ErrorFormatter, loc_t) -> None
        errfmt.loc_stack.append(location)
        self.errfmt = errfmt

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.errfmt.loc_stack.pop()


# TODO:
# - ColorErrorFormatter
# - BareErrorFormatter?  Could just display the foo.sh:37:8: and not quotation.
#
# Are these controlled by a flag?  It's sort of like --comp-ui.  Maybe
# --error-ui.


class ErrorFormatter(object):
    """Print errors with code excerpts.

    Philosophy:
    - There should be zero or one code quotation when a shell exits non-zero.
      Showing the same line twice is noisy.
    - When running parallel processes, avoid interleaving multi-line code
      quotations.  (TODO: turn off in child processes?)
    """

    def __init__(self):
        # type: () -> None
        self.loc_stack = []  # type: List[loc_t]
        self.one_line_errexit = False  # root process

    def OneLineErrExit(self):
        # type: () -> None
        """Unused now.

        For SubprogramThunk.
        """
        self.one_line_errexit = True

    # A stack used for the current builtin.  A fallback for UsageError.
    # TODO: Should we have PushBuiltinName?  Then we can have a consistent style
    # like foo.sh:1: (compopt) Not currently executing.
    def _FallbackLocation(self, blame_loc):
        # type: (Optional[loc_t]) -> loc_t
        if blame_loc is None or blame_loc.tag() == loc_e.Missing:
            if len(self.loc_stack):
                return self.loc_stack[-1]
            return loc.Missing

        return blame_loc

    def PrefixPrint(self, msg, prefix, blame_loc):
        # type: (str, str, loc_t) -> None
        """Print a hard-coded message with a prefix, and quote code."""
        _PrintWithLocation(prefix,
                           msg,
                           self._FallbackLocation(blame_loc),
                           show_code=True)

    def Print_(self, msg, blame_loc=None):
        # type: (str, loc_t) -> None
        """Print message and quote code."""
        _PrintWithLocation('',
                           msg,
                           self._FallbackLocation(blame_loc),
                           show_code=True)

    def PrintMessage(self, msg, blame_loc=None):
        # type: (str, loc_t) -> None
        """Print a message WITHOUT quoting code."""
        _PrintWithLocation('',
                           msg,
                           self._FallbackLocation(blame_loc),
                           show_code=False)

    def StderrLine(self, msg):
        # type: (str) -> None
        """Just print to stderr."""
        print_stderr(msg)

    def PrettyPrintError(self, err, prefix=''):
        # type: (_ErrorWithLocation, str) -> None
        """Print an exception that was caught, with a code quotation.

        Unlike other methods, this doesn't use the GetLocationForLine()
        fallback. That only applies to builtins; instead we check
        e.HasLocation() at a higher level, in CommandEvaluator.
        """
        # TODO: Should there be a special span_id of 0 for EOF?  runtime.NO_SPID
        # means there is no location info, but 0 could mean that the location is EOF.
        # So then you query the arena for the last line in that case?
        # Eof_Real is the ONLY token with 0 span, because it's invisible!
        # Well Eol_Tok is a sentinel with span_id == runtime.NO_SPID.  I think that
        # is OK.
        # Problem: the column for Eof could be useful.

        _PrintWithLocation(prefix, err.UserErrorString(), err.location, True)

    def PrintErrExit(self, err, pid):
        # type: (error.ErrExit, int) -> None

        # TODO:
        # - Don't quote code if you already quoted something on the same line?
        #   - _PrintWithLocation calculates the line_id.  So you need to remember that?
        #   - return it here?
        prefix = 'errexit PID %d: ' % pid
        _PrintWithLocation(prefix, err.UserErrorString(), err.location,
                           err.show_code)


def PrintAst(node, flag):
    # type: (command_t, arg_types.main) -> None

    if flag.ast_format == 'none':
        print_stderr('AST not printed.')
        if 0:
            from _devbuild.gen.id_kind_asdl import Id_str
            from frontend.lexer import ID_HIST, LAZY_ID_HIST

            print(LAZY_ID_HIST)
            print(len(LAZY_ID_HIST))

            for id_, count in ID_HIST.most_common(10):
                print('%8d %s' % (count, Id_str(id_)))
            print()
            total = sum(ID_HIST.values())
            uniq = len(ID_HIST)
            print('%8d total tokens' % total)
            print('%8d unique tokens IDs' % uniq)
            print()

            for id_, count in LAZY_ID_HIST.most_common(10):
                print('%8d %s' % (count, Id_str(id_)))
            print()
            total = sum(LAZY_ID_HIST.values())
            uniq = len(LAZY_ID_HIST)
            print('%8d total tokens' % total)
            print('%8d tokens with LazyVal()' % total)
            print('%8d unique tokens IDs' % uniq)
            print()

        if 0:
            from osh.word_parse import WORD_HIST
            #print(WORD_HIST)
            for desc, count in WORD_HIST.most_common(20):
                print('%8d %s' % (count, desc))

    else:  # text output
        f = mylib.Stdout()

        do_abbrev = 'abbrev-' in flag.ast_format
        perf_stats = flag.ast_format.startswith('__')  # __perf or __dumpdoc

        if perf_stats:
            log('')
            log('___ GC: after parsing')
            mylib.PrintGcStats()
            log('')

        tree = node.PrettyTree(do_abbrev)

        if perf_stats:
            # Warning: __dumpdoc should only be passed with tiny -c fragments.
            # This tree is huge and can eat up all memory.
            fmt._HNodePrettyPrint(True,
                                  flag.ast_format == '__dumpdoc',
                                  tree,
                                  f,
                                  max_width=_GetMaxWidth())
        else:
            fmt.HNodePrettyPrint(tree, f, max_width=_GetMaxWidth())


def TypeNotPrinted(val):
    # type: (value_t) -> bool
    return val.tag() in (value_e.Null, value_e.Bool, value_e.Int,
                         value_e.Float, value_e.Str, value_e.List,
                         value_e.Dict, value_e.Obj)


def _GetMaxWidth():
    # type: () -> int
    max_width = 80  # default value
    try:
        width = libc.get_terminal_width()
        if width > 0:
            max_width = width
    except (IOError, OSError):
        pass  # leave at default

    return max_width


def PrettyPrintValue(prefix, val, f, max_width=-1):
    # type: (str, value_t, mylib.Writer, int) -> None
    """For the = keyword"""

    encoder = pp_value.ValueEncoder()
    encoder.SetUseStyles(f.isatty())

    # TODO: pretty._Concat, etc. shouldn't be private
    if TypeNotPrinted(val):
        mdocs = encoder.TypePrefix(pp_value.ValType(val))
        mdocs.append(encoder.Value(val))
        doc = pretty._Concat(mdocs)
    else:
        doc = encoder.Value(val)

    if len(prefix):
        # If you want the type name to be indented, which we don't
        # inner = pretty._Concat([pretty._Break(""), doc])

        doc = pretty._Concat([
            pretty.AsciiText(prefix),
            #pretty._Break(""),
            pretty._Indent(4, doc)
        ])

    if max_width == -1:
        max_width = _GetMaxWidth()

    printer = pretty.PrettyPrinter(max_width)

    buf = mylib.BufWriter()
    printer.PrintDoc(doc, buf)
    f.write(buf.getvalue())
    f.write('\n')


def PrintShFunction(proc_val):
    # type: (value.Proc) -> None
    if proc_val.code_str is not None:
        print(proc_val.code_str)
    else:
        print('%s() { : "function body not available"; }' % proc_val.name)

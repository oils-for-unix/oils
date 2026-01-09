"""Glob_.py."""

import libc

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.syntax_asdl import (CompoundWord, Token, word_part_e,
                                       glob_part, glob_part_e, glob_part_t,
                                       loc, loc_t)
from _devbuild.gen.value_asdl import value
from core import pyos, pyutil, error
from frontend import match
from mycpp import mylib
from mycpp.mylib import log
from pylib import os_path

from libc import GLOB_PERIOD, FNM_PATHNAME
from _devbuild.gen.value_asdl import value_e
from _devbuild.gen.runtime_asdl import scope_e

from typing import Dict, List, Tuple, cast, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from core import optview
    from core import state
    from frontend.match import SimpleLexer

_ = log


def LooksLikeGlob(s):
    # type: (str) -> bool
    """Does this string look like a glob pattern?

    Like other shells, OSH avoids calls to glob() unless there are glob
    metacharacters.

    TODO: Reference lib/glob /   glob_pattern functions in bash
    $ grep glob_pattern lib/glob/*

    Used:
    1. in Globber below
    2. for the slow path / fast path of prefix/suffix/patsub ops.
    """
    left_bracket = False
    i = 0
    n = len(s)
    while i < n:
        c = mylib.ByteAt(s, i)

        if mylib.ByteEquals(c, '\\'):
            i += 1

        elif mylib.ByteEquals(c, '*') or mylib.ByteEquals(c, '?'):
            return True

        elif mylib.ByteEquals(c, '['):
            left_bracket = True

        elif mylib.ByteEquals(c, ']') and left_bracket:
            # It has at least one pair of balanced [].  Not bothering to check stray
            # [ or ].
            return True

        i += 1
    return False


def LooksLikeStaticGlob(w):
    # type: (CompoundWord) -> bool
    """Like LooksLikeGlob, but for static words."""

    left_bracket = False
    for part in w.parts:
        if part.tag() == word_part_e.Literal:
            id_ = cast(Token, part).id
            if id_ in (Id.Lit_Star, Id.Lit_QMark):
                return True
            elif id_ == Id.Lit_LBracket:
                left_bracket = True
            elif id_ == Id.Lit_RBracket and left_bracket:
                return True
    return False


# Glob Helpers for WordParts.
# NOTE: Escaping / doesn't work, because it's not a filename character.
# ! : - are metachars within character classes
# ( ) | are extended glob characters, and it's OK to add extra \ when the
#       underlying library doesn't support extended globs
#       we don't need to escape the @ in @(cc), because escaping ( is enough
GLOB_META_CHARS = r'\*?[]-:!()|'

# Check invariant needed to escape literal \ as \@
assert '@' not in GLOB_META_CHARS, '\@ is used to escape backslash'


def GlobEscape(s):
    # type: (str) -> str
    """For SingleQuoted, DoubleQuoted, and EscapedLiteral."""
    return pyutil.BackslashEscape(s, GLOB_META_CHARS)


def GlobEscapeBackslash(s):
    # type: (str) -> str
    """Glob escape a string for an unquoted var sub.

    Used to evaluate something like *$v with v='a\*b.txt'

    We escape \ as \@, which is OK because @ is not in GLOB_META_CHARS.

    See test cases in spec/glob.test.sh

    - If globbing is performed, then \* evaluates to literal '*'
      - that is, \ is an escape for the *
    - If globbing is NOT performed (set -o noglob or no matching files), then
      \* evaluates to '\*'
      - that is, the \ is preserved literally
    """
    return s.replace('\\', r'\@')


# Bug fix: add [] so [[:space:]] is not special, etc.
ERE_META_CHARS = r'\?*+{}^$.()|[]'


def ExtendedRegexEscape(s):
    # type: (str) -> str
    """Quoted parts need to be regex-escaped when quoted, e.g. [[ $a =~ "{" ]].
    I don't think libc has a function to do this.  Escape these characters:

    https://www.gnu.org/software/sed/manual/html_node/ERE-syntax.html
    """
    return pyutil.BackslashEscape(s, ERE_META_CHARS)


def GlobUnescape(s):
    # type: (str) -> str
    """Remove glob escaping from a string.

    Used when there is no glob match.
    TODO: Can probably get rid of this, as long as you save the original word.

    Complicated example: 'a*b'*.py, which will be escaped to a\*b*.py.  So in
    word_eval _JoinElideEscape and EvalWordToString you have to build two
    'parallel' strings -- one escaped and one not.
    """
    unescaped = []  # type: List[int]
    i = 0
    n = len(s)
    while i < n:
        c = mylib.ByteAt(s, i)

        if mylib.ByteEquals(c, '\\') and i != n - 1:
            # TODO: GlobEscape() turns \ into \\, so a string should never end
            # with a single backslash.
            # Suppressed this assert to fix bug #698, #628 is still there.
            # Check them again.
            assert i != n - 1, 'Trailing backslash: %r' % s

            i += 1
            c2 = mylib.ByteAt(s, i)

            if mylib.ByteInSet(c2, GLOB_META_CHARS):
                unescaped.append(c2)
            elif mylib.ByteEquals(c2, '@'):
                unescaped.append(pyos.BACKSLASH_CH)
            else:
                raise AssertionError("Unexpected escaped character %r" % c2)
        else:
            unescaped.append(c)
        i += 1
    return mylib.JoinBytes(unescaped)


def GlobUnescapeBackslash(s):
    # type: (str) -> str
    """Inverse of GlobEscapeBackslash - turns \@ into \ """
    return s.replace('\\@', '\\')


# For ${x//foo*/y}, we need to glob patterns, but fnmatch doesn't give you the
# positions of matches.  So we convert globs to regexps.

# Problems:
# - What about unicode?  Do we have to set any global variables?  We want it to
#   always use utf-8?


class _GlobParser(object):

    def __init__(self, lexer):
        # type: (SimpleLexer) -> None
        self.lexer = lexer
        self.token_type = Id.Undefined_Tok
        self.token_val = ''
        self.warnings = []  # type: List[str]

    def _Next(self):
        # type: () -> None
        """Move to the next token."""
        self.token_type, self.token_val = self.lexer.Next()

    def _ParseCharClass(self):
        # type: () -> List[glob_part_t]
        """
        Returns:
          a CharClass if the parse succeeds, or a Literal if fails.  In the latter
          case, we also append a warning.
        """
        first_token = glob_part.Literal(self.token_type, self.token_val)
        balance = 1  # We already saw a [
        tokens = []  # type: List[Tuple[Id_t, str]]

        # NOTE: There is a special rule where []] and [[] are valid globs.  Also
        # [^[] and sometimes [^]], although that one is ambiguous!
        # And [[:space:]] and [[.class.]] has to be taken into account too.  I'm
        # punting on this now because the rule isn't clear and consistent between
        # shells.

        while True:
            self._Next()

            if self.token_type == Id.Eol_Tok:
                # TODO: location info
                self.warnings.append(
                    'Malformed character class; treating as literal')
                parts = [first_token]  # type: List[glob_part_t]
                for (id_, s) in tokens:
                    parts.append(glob_part.Literal(id_, s))
                return parts

            if self.token_type == Id.Glob_LBracket:
                balance += 1
            elif self.token_type == Id.Glob_RBracket:
                balance -= 1

            if balance == 0:
                break
            tokens.append(
                (self.token_type, self.token_val))  # Don't append the last ]

        negated = False
        if len(tokens):
            id1, _ = tokens[0]
            # NOTE: Both ! and ^ work for negation in globs
            # https://www.gnu.org/software/bash/manual/html_node/Pattern-Matching.html#Pattern-Matching
            # TODO: Warn about the one that's not recommended?
            if id1 in (Id.Glob_Bang, Id.Glob_Caret):
                negated = True
                tokens = tokens[1:]
        strs = [s for _, s in tokens]
        return [glob_part.CharClass(negated, strs)]

    def Parse(self):
        # type: () -> Tuple[List[glob_part_t], List[str]]
        """
        Returns:
          regex string (or None if it's not a glob)
          A list of warnings about the syntax
        """
        parts = []  # type: List[glob_part_t]

        while True:
            self._Next()
            id_ = self.token_type
            s = self.token_val

            #log('%s %r', self.token_type, self.token_val)
            if id_ == Id.Eol_Tok:
                break

            if id_ in (Id.Glob_Star, Id.Glob_QMark):
                parts.append(glob_part.Operator(id_))

            elif id_ == Id.Glob_LBracket:
                # Could return a Literal or a CharClass
                parts.extend(self._ParseCharClass())

            else:  # Glob_{Bang,Caret,CleanLiterals,OtherLiteral,RBracket,EscapedChar,
                #       BadBackslash}
                parts.append(glob_part.Literal(id_, s))

            # Also check for warnings.  TODO: location info.
            if id_ == Id.Glob_RBracket:
                self.warnings.append('Got unescaped right bracket')
            if id_ == Id.Glob_BadBackslash:
                self.warnings.append('Got unescaped trailing backslash')

        return parts, self.warnings


_REGEX_CHARS_TO_ESCAPE = '.|^$()+*?[]{}\\'


def _GenerateERE(parts):
    # type: (List[glob_part_t]) -> str
    out = []  # type: List[str]

    for part in parts:
        tag = part.tag()
        UP_part = part

        if tag == glob_part_e.Literal:
            part = cast(glob_part.Literal, UP_part)
            if part.id == Id.Glob_EscapedChar:
                assert len(part.s) == 2, part.s
                # The user could have escaped a char that doesn't need regex escaping,
                # like \b or something.
                c = part.s[1]
                if c in _REGEX_CHARS_TO_ESCAPE:
                    out.append('\\')
                out.append(c)

            # ! is only for char class
            elif part.id in (Id.Glob_CleanLiterals, Id.Glob_Bang):
                out.append(part.s)  # e.g. 'py' doesn't need to be escaped

            # ^ is only for char class
            elif part.id in (Id.Glob_OtherLiteral, Id.Glob_Caret):
                assert len(part.s) == 1, part.s
                c = part.s
                if c in _REGEX_CHARS_TO_ESCAPE:
                    out.append('\\')
                out.append(c)

            # These are UNMATCHED ones not parsed in a glob class
            elif part.id == Id.Glob_LBracket:
                out.append('\\[')

            elif part.id == Id.Glob_RBracket:
                out.append('\\]')

            elif part.id == Id.Glob_BadBackslash:
                out.append('\\\\')

            elif part.id == Id.Glob_Caret:
                out.append('^')

            else:
                raise AssertionError(part.id)

        elif tag == glob_part_e.Operator:
            part = cast(glob_part.Operator, UP_part)
            if part.op_id == Id.Glob_QMark:
                out.append('.')
            elif part.op_id == Id.Glob_Star:
                out.append('.*')
            else:
                raise AssertionError()

        elif tag == glob_part_e.CharClass:
            part = cast(glob_part.CharClass, UP_part)
            out.append('[')
            if part.negated:
                out.append('^')

            # Important: the character class is LITERALLY preserved, because we
            # assume glob char classes are EXACTLY the same as regex char classes,
            # including the escaping rules.
            #
            # TWO WEIRD EXCEPTIONS:
            # \- is moved to the end as '-'.
            #   In GNU libc, [0\-9] ODDLY has a range starting with \ !  But we
            #   want a literal, and the POSIX way to do that is to put it at the end.
            # \] is moved to the FRONT as ]

            good = []  # type: List[str]

            literal_hyphen = False
            literal_rbracket = False

            for s in part.strs:
                if s == '\-':
                    literal_hyphen = True
                    continue
                if s == '\]':
                    literal_rbracket = True
                    continue
                good.append(s)

            if literal_rbracket:
                out.append(']')

            out.extend(good)

            if literal_hyphen:
                out.append('-')

            out.append(']')

    return ''.join(out)


def GlobToERE(pat):
    # type: (str) -> Tuple[str, List[str]]
    lexer = match.GlobLexer(pat)
    p = _GlobParser(lexer)
    parts, warnings = p.Parse()

    # Vestigial: if there is nothing like * ? or [abc], then the whole string is
    # a literal, and we could use a more efficient mechanism.
    # But we would have to DEQUOTE before doing that.
    if 0:
        is_glob = False
        for p in parts:
            if p.tag in (glob_part_e.Operator, glob_part_e.CharClass):
                is_glob = True
    if 0:
        log('GlobToERE()')
        for p in parts:
            log('  %s', p)

    regex = _GenerateERE(parts)
    #log('pat %s -> regex %s', pat, regex)
    return regex, warnings


# Notes for implementing extglob
# - libc glob() doesn't have any extension!
# - Nix stdenv uses !(foo) and @(foo|bar)
#   - can we special case these for now?
# - !(foo|bar) -- change it to *, and then just do fnmatch() to filter the
# result!
# - Actually I guess we can do that for all of them.  That seems fine.
# - But we have to get the statically parsed arg in here?
#   - or do dynamic parsing
#     - LooksLikeGlob() would have to respect extglob!  ugh!
# - See 2 calls in osh/word_eval.py


def _StringMatchesAnyPattern(s, patterns):
    # type: (str, List[str]) -> bool
    """Check if string matches any pattern in the list.

    Returns True if s matches any pattern, or if s is . or ..
    (which are always filtered when GLOBIGNORE is set).
    """
    for pattern in patterns:
        if libc.fnmatch(pattern, s, FNM_PATHNAME):
            return True

    return False


class Globber(object):

    def __init__(self, exec_opts, mem):
        # type: (optview.Exec, state.Mem) -> None
        self.exec_opts = exec_opts
        self.mem = mem
        # Cache for parsed GLOBIGNORE patterns to avoid re-parsing
        self._globignore_cache = {}  # type: Dict[str, List[str]]

        # Other unimplemented bash options:
        #
        # globstar          ** for directories
        # globasciiranges   ascii or unicode char classes (unicode by default)
        # nocaseglob
        # GLOBSORT global variable

    def _GetGlobIgnorePatterns(self):
        # type: () -> Optional[List[str]]
        """Get GLOBIGNORE patterns as a list, or None if not set."""

        val = self.mem.GetValue('GLOBIGNORE', scope_e.GlobalOnly)
        if val.tag() != value_e.Str:
            return None

        globignore = cast(value.Str, val).s  # type: str
        if len(globignore) == 0:
            return None

        if globignore in self._globignore_cache:
            return self._globignore_cache[globignore]

        # Split by colon to get individual patterns, but don't split colons
        # inside bracket expressions like [[:alnum:]]
        patterns = []  # type: List[str]
        current = []  # type: List[str]
        in_bracket = False

        for c in globignore:
            if c == '[':
                in_bracket = True
                current.append(c)
            elif c == ']':
                in_bracket = False
                current.append(c)
            elif c == ':' and not in_bracket:
                if len(current):
                    patterns.append(''.join(current))
                    del current[:]
            else:
                current.append(c)

        if len(current):
            patterns.append(''.join(current))

        self._globignore_cache[globignore] = patterns

        return patterns

    def DoLibcGlob(self, arg, out, blame_loc):
        # type: (str, List[str], loc_t) -> None
        """For the io.libcGlob() API"""
        try:
            results = libc.glob(arg, 0)
        except RuntimeError as e:
            # Rare glob errors, like GLOB_NOSPACE
            # Note: dash has a fatal sh_error() on GLOB_NOSPACE

            # note: MyPy doesn't know RuntimeError has e.message (and e.args)
            msg = e.message  # type: str
            raise error.Structured(error.CODEC_STATUS, msg, blame_loc)

        out.extend(results)

    def DoShellGlob(self, arg, out, blame_loc=loc.Missing):
        # type: (str, List[str], loc_t) -> int
        """For word evaluation and the io.glob() API

        Respects these filters:
        - GLOBIGNORE
        - dotglob turns into C GLOB_PERIOD
        - no_dash_glob
        - globskipdots

        But NOT these; they are done at a higher level
        - noglob 
        - failglob
        - nullglob - ditto

        TODO:
        - ysh globbing should not respect globals like GLOBIGNORE?
          - only no_dash_glob by default?
        - split into two functions:
          - compatible io.glob()
          - controlled io.libcGlob()
        """
        globignore_patterns = self._GetGlobIgnorePatterns()

        flags = 0
        # shopt -u dotglob (default): echo * does not return say .gitignore
        # If GLOBIGNORE is set, then dotglob is NOT respected - we return ..
        if self.exec_opts.dotglob() or globignore_patterns is not None:
            # If HAVE_GLOB_PERIOD is false, then ./configure stubs out
            # GLOB_PERIOD as 0, a no-op
            flags |= GLOB_PERIOD

        try:
            results = libc.glob(arg, flags)
        except RuntimeError as e:
            # Rare glob errors, like GLOB_NOSPACE
            # Note: dash has a fatal sh_error() on GLOB_NOSPACE

            # note: MyPy doesn't know RuntimeError has e.message (and e.args)
            msg = e.message  # type: str
            raise error.Structured(error.CODEC_STATUS, msg, blame_loc)
        #log('glob %r -> %r', arg, g)

        if len(results) == 0:
            return 0  # nothing matched

        # Something matched

        if globignore_patterns is not None:  # Handle GLOBIGNORE
            # When GLOBIGNORE is set, bash doesn't respect shopt -u
            # globskipdots!  The entries . and .. are skipped, even if they
            # do NOT match GLOBIGNORE
            tmp = [
                s for s in results
                if not _StringMatchesAnyPattern(s, globignore_patterns) and
                os_path.basename(s) not in ('.', '..')
            ]
            results = tmp  # idiom to work around mycpp limitation

            skipdots = True

        else:  # Do filtering that's NOT GLOBIGNORE
            # no_dash_glob: Omit files starting with -
            # (part of shopt --set ysh:upgrade)
            if self.exec_opts.no_dash_glob():
                tmp = [s for s in results if not s.startswith('-')]
                results = tmp

            # globskipdots: Remove . and .. entries returned by libc.
            if self.exec_opts.globskipdots():
                tmp = [s for s in results if s not in ('.', '..')]
                results = tmp

        out.extend(results)
        return len(results)

    def Expand(self, arg, out, blame_loc):
        # type: (str, List[str], loc_t) -> int
        """Given a string that MAY be a glob, perform glob expansion

        If files on disk match the glob pattern, we append to the list 'out',
        and return the number of items.

        Returns:
          Number of items appended, or -1 when glob expansion did not happen.
        Raises:
          error.FailGlob when nothing matched, and shopt -s failglob
        """
        if self.exec_opts.noglob():
            # The caller should use the original string
            return -1

        n = self.DoShellGlob(arg, out)
        if n:
            return n

        # Nothing matched
        if self.exec_opts.failglob():
            raise error.FailGlob('Pattern %r matched no files' % arg,
                                 blame_loc)

        if self.exec_opts.nullglob():
            return 0

        # The caller should use the original string
        return -1

    def ExpandExtended(self, glob_pat, fnmatch_pat, out):
        # type: (str, str, List[str]) -> int
        """
        Returns:
          The number of items appended, or -1 when glob expansion did not happen
        """
        if self.exec_opts.noglob():
            # Return the fnmatch_pat.  Note: this means we turn ,() into @(), and
            # there is extra \ escaping compared with bash and mksh.  OK for now
            out.append(fnmatch_pat)
            return 1

        tmp = []  # type: List[str]
        self.DoShellGlob(glob_pat, tmp)
        filtered = [s for s in tmp if libc.fnmatch(fnmatch_pat, s)]
        n = len(filtered)

        if n:
            out.extend(filtered)
            return n

        if self.exec_opts.failglob():
            return -1  # nothing matched

        if self.exec_opts.nullglob():
            return 0

        # Expand to fnmatch_pat, as above
        out.append(GlobUnescape(fnmatch_pat))
        return 1

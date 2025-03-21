"""
split.py - Word Splitting

Nice blog post on the complexity/corner cases/differing intuition of splitting
strings:

https://chriszetter.com/blog/2017/10/29/splitting-strings/

python-dev doesn't want to touch it anymore!

Other possible splitters:

- AwkSplitter -- how does this compare to awk -F?
- RegexSplitter
- CsvSplitter
- TSV2Splitter -- Data is transformed because of # \u0065 in JSON.  So it's not
  a pure slice, but neither is IFS splitting because of backslashes.
- Perl?
  - does perl have a spilt context?

with SPLIT_REGEX = / digit+ / {
  echo $#
  echo $len(argv)
  echo $1 $2
  echo @argv
}
"""

from _devbuild.gen.runtime_asdl import (scope_e, span_e, emit_i, char_kind_i,
                                        state_i)
from _devbuild.gen.value_asdl import (value, value_e, value_t)
from mycpp.mylib import log
from core import pyutil
from frontend import consts
from mycpp import mylib
from mycpp.mylib import tagswitch

from typing import List, Tuple, Dict, Optional, TYPE_CHECKING, cast
if TYPE_CHECKING:
    from core.state import Mem
    from _devbuild.gen.runtime_asdl import span_t
    Span = Tuple[span_t, int]

DEFAULT_IFS = ' \t\n'


def _SpansToParts(s, spans):
    # type: (str, List[Span]) -> List[str]
    """Helper for SplitForWordEval."""
    parts = []  # type: List[mylib.BufWriter]
    start_index = 0

    # If the last span was black, and we get a backslash, set join_next to merge
    # two black spans.
    join_next = False
    last_span_was_black = False

    for span_type, end_index in spans:
        if span_type == span_e.Black:
            if len(parts) and join_next:
                parts[-1].write(s[start_index:end_index])
                join_next = False
            else:
                buf = mylib.BufWriter()
                buf.write(s[start_index:end_index])
                parts.append(buf)

            last_span_was_black = True

        elif span_type == span_e.Backslash:
            if last_span_was_black:
                join_next = True
            last_span_was_black = False

        else:
            last_span_was_black = False

        start_index = end_index

    result = [buf.getvalue() for buf in parts]
    return result


class SplitContext(object):
    """A polymorphic interface to field splitting.

    It respects a STACK of IFS values, for example:

    echo $x  # uses default shell IFS
    IFS=':' myfunc  # new splitter
    echo $x  # uses default shell IFS again.
    """

    def __init__(self, mem):
        # type: (Mem) -> None
        self.mem = mem
        # Split into (ifs_whitespace, ifs_other)
        self.splitters = {
        }  # type: Dict[str, IfsSplitter]  # aka IFS value -> splitter instance

    def _GetSplitter(self, ifs=None):
        # type: (str) -> IfsSplitter
        """Based on the current stack frame, get the splitter."""
        if ifs is None:
            # Like _ESCAPER, this has dynamic scope!
            val = self.mem.GetValue('IFS', scope_e.Dynamic)

            UP_val = val
            with tagswitch(val) as case:
                if case(value_e.Undef):
                    ifs = DEFAULT_IFS
                elif case(value_e.Str):
                    val = cast(value.Str, UP_val)
                    ifs = val.s
                else:
                    # TODO: Raise proper error
                    raise AssertionError("IFS shouldn't be an array")

        sp = self.splitters.get(ifs)  # cache lookup
        if sp is None:
            # Figure out what kind of splitter we should instantiate.

            ifs_whitespace = mylib.BufWriter()
            ifs_other = mylib.BufWriter()
            for c in ifs:
                if c in ' \t\n':  # Happens to be the same as DEFAULT_IFS
                    ifs_whitespace.write(c)
                else:
                    # TODO: \ not supported
                    ifs_other.write(c)

            sp = IfsSplitter(ifs_whitespace.getvalue(), ifs_other.getvalue())

            # NOTE: Technically, we could make the key more precise.  IFS=$' \t' is
            # the same as IFS=$'\t '.  But most programs probably don't do that, and
            # everything should work in any case.
            self.splitters[ifs] = sp

        return sp

    def GetJoinChar(self):
        # type: () -> str
        """For decaying arrays by joining, eg.

        "$@" -> $@. array
        """
        # https://www.gnu.org/software/bash/manual/bashref.html#Special-Parameters
        # http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_05_02
        # "When the expansion occurs within a double-quoted string (see
        # Double-Quotes), it shall expand to a single field with the value of
        # each parameter separated by the first character of the IFS variable, or
        # by a <space> if IFS is unset. If IFS is set to a null string, this is
        # not equivalent to unsetting it; its first character does not exist, so
        # the parameter values are concatenated."
        val = self.mem.GetValue('IFS', scope_e.Dynamic)  # type: value_t
        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Undef):
                return ' '
            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if len(val.s):
                    return val.s[0]
                else:
                    return ''
            else:
                # TODO: Raise proper error
                raise AssertionError("IFS shouldn't be an array")

        raise AssertionError('for -Wreturn-type in C++')

    def Escape(self, s):
        # type: (str) -> str
        """Escape IFS chars."""
        sp = self._GetSplitter()
        return sp.Escape(s)

    def SplitForWordEval(self, s, ifs=None):
        # type: (str, Optional[str]) -> List[str]
        """Split used by word evaluation.

        Also used by the explicit shSplit() function.
        """
        sp = self._GetSplitter(ifs=ifs)
        spans = sp.Split(s, True)

        # Note: pass allow_escape=False so \ isn't special
        #spans = sp.Split(s, False)

        if 0:
            for span in spans:
                log('SPAN %s', span)
        return _SpansToParts(s, spans)

    def SplitForRead(self, line, allow_escape, do_split):
        # type: (str, bool, bool) -> List[Span]

        # None: use the default splitter, consulting $IFS
        # ''  : forces IFS='' behavior
        ifs = None if do_split else ''

        sp = self._GetSplitter(ifs=ifs)
        return sp.Split(line, allow_escape)


class _BaseSplitter(object):

    def __init__(self, escape_chars):
        # type: (str) -> None
        self.escape_chars = escape_chars + '\\'  # Backslash is always escaped

    def Escape(self, s):
        # type: (str) -> str
        # Note the characters here are DYNAMIC, unlike other usages of
        # BackslashEscape().
        return pyutil.BackslashEscape(s, self.escape_chars)


class IfsSplitter(_BaseSplitter):
    """Split a string when IFS has non-whitespace characters."""

    def __init__(self, ifs_whitespace, ifs_other):
        # type: (str, str) -> None
        _BaseSplitter.__init__(self, ifs_whitespace + ifs_other)
        self.ifs_whitespace = ifs_whitespace
        self.ifs_other = ifs_other

    def __repr__(self):
        # type: () -> str
        return '<IfsSplitter whitespace=%r other=%r>' % (self.ifs_whitespace,
                                                         self.ifs_other)

    def Split(self, s, allow_escape):
        # type: (str, bool) -> List[Span]
        """
        Args:
          s: string to split
          allow_escape: False for read -r, this means \ doesn't do anything.

        Returns:
          List of (runtime.span, end_index) pairs
        """
        ws_chars = self.ifs_whitespace
        other_chars = self.ifs_other

        n = len(s)
        # NOTE: in C, could reserve() this to len(s)
        spans = []  # type: List[Span]

        if n == 0:
            return spans  # empty

        # Ad hoc rule from POSIX: ignore leading whitespace.
        # "IFS white space shall be ignored at the beginning and end of the input"
        # This can't really be handled by the state machine.

        # 2025-03: This causes a bug with splitting ""$A"" when there's no IFS

        i = 0
        while i < n and mylib.ByteInSet(mylib.ByteAt(s, i), ws_chars):
            i += 1

        # Append an ignored span.
        if i != 0:
            spans.append((span_e.Delim, i))

        # String is ONLY whitespace.  We want to skip the last span after the
        # while loop.
        if i == n:
            return spans

        state = state_i.Start
        while state != state_i.Done:
            if i < n:
                byte = mylib.ByteAt(s, i)

                if mylib.ByteInSet(byte, ws_chars):
                    ch = char_kind_i.DE_White
                elif mylib.ByteInSet(byte, other_chars):
                    ch = char_kind_i.DE_Gray
                elif allow_escape and mylib.ByteEquals(byte, '\\'):
                    ch = char_kind_i.Backslash
                else:
                    ch = char_kind_i.Black

            elif i == n:
                ch = char_kind_i.Sentinel  # one more iterations for the end of string

            else:
                raise AssertionError()  # shouldn't happen

            new_state, action = consts.IfsEdge(state, ch)
            if new_state == state_i.Invalid:
                raise AssertionError('Invalid transition from %r with %r' %
                                     (state, ch))

            if 0:
                log('i %d byte %r ch %s current: %s next: %s %s', i, byte, ch,
                    state, new_state, action)

            if action == emit_i.Part:
                spans.append((span_e.Black, i))
            elif action == emit_i.Delim:
                spans.append((span_e.Delim, i))  # ignored delimiter
            elif action == emit_i.Empty:
                spans.append((span_e.Delim, i))  # ignored delimiter
                # EMPTY part that is NOT ignored
                spans.append((span_e.Black, i))
            elif action == emit_i.Escape:
                spans.append((span_e.Backslash, i))  # \
            elif action == emit_i.Nothing:
                pass
            else:
                raise AssertionError()

            state = new_state
            i += 1

        return spans

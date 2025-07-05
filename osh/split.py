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

from _devbuild.gen.runtime_asdl import (scope_e, state_i)
from _devbuild.gen.value_asdl import (value, value_e, value_t)
from mycpp.mylib import log
from core import pyutil, pyos
from frontend import consts
from mycpp import mylib
from mycpp.mylib import tagswitch
from osh import glob_

from typing import List, Tuple, Dict, Optional, TYPE_CHECKING, cast
if TYPE_CHECKING:
    from core.state import Mem

DEFAULT_IFS = ' \t\n'


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

    def CreateSplitterState(self, ifs=None):
        # type: (Optional[str]) -> IfsSplitterState
        sp = self._GetSplitter(ifs=ifs)
        return IfsSplitterState(sp.ifs_whitespace, sp.ifs_other)

    def SplitForWordEval(self, s, ifs=None):
        # type: (str, Optional[str]) -> List[str]
        """Split used by the explicit shSplit() function.
        """
        sp = self.CreateSplitterState(ifs=ifs)
        sp.allow_escape = True
        sp.PushFragment(s)
        return sp.PushTerminator()

    def SplitForRead(self, line, allow_escape, do_split, max_parts):
        # type: (str, bool, bool, int) -> List[str]

        if len(line) == 0:
            return []

        # None: use the default splitter, consulting $IFS
        # ''  : forces IFS='' behavior
        ifs = None if do_split else ''

        sp = self.CreateSplitterState(ifs=ifs)
        sp.allow_escape = allow_escape
        sp.max_split = max_parts - 1
        sp.PushFragment(line)
        return sp.PushTerminator()


class IfsSplitter(object):
    """Split a string when IFS has non-whitespace characters."""

    def __init__(self, ifs_whitespace, ifs_other):
        # type: (str, str) -> None
        self.ifs_whitespace = ifs_whitespace
        self.ifs_other = ifs_other

    def __repr__(self):
        # type: () -> str
        return '<IfsSplitter whitespace=%r other=%r>' % (self.ifs_whitespace,
                                                         self.ifs_other)


class IfsSplitterState(object):

    def __init__(self, ifs_space, ifs_other):
        # type: (str, str) -> None
        self.ifs_space = ifs_space
        self.ifs_other = ifs_other
        self.glob_escape = False
        self.allow_escape = False
        self.max_split = -1
        self.Reset()

    def Reset(self):
        # type: () -> None
        self.state = state_i.Start
        self.args = []  # type: List[str]  # generated words
        self.frags = []  # type: List[str]  # str fragments of the current word
        self.char_buff = []  # type: List[int]  # chars in the current fragment
        self.max_split_trim = 0  # Number of IFS chars to trim from right

    def _FlushCharBuff(self):
        # type: () -> None
        if len(self.char_buff) >= 1:
            if self.max_split_trim > 0:
                self.char_buff = self.char_buff[0:-self.max_split_trim]
                self.max_split_trim = 0
            frag = mylib.JoinBytes(self.char_buff)
            if self.glob_escape:
                frag = glob_.GlobEscapeUnquotedSubstitution(frag)
            self.frags.append(frag)
            self.char_buff = []

    def _GenerateWord(self):
        # type: () -> None
        self._FlushCharBuff()
        self.args.append(''.join(self.frags))
        self.frags = []

    def PushLiteral(self, s):
        # type: (str) -> None
        """
        Args:
          s: word fragment that should be literally added
        """
        self.max_split_trim = 0
        if self.state == state_i.White:
            self._GenerateWord()
        else:
            self._FlushCharBuff()
        self.frags.append(s)
        self.state = state_i.Black

    def PushFragment(self, s):
        # type: (str) -> None
        """
        Args:
          s: word fragment to split
        """

        ifs_space = self.ifs_space
        ifs_other = self.ifs_other
        allow_escape = self.allow_escape
        max_split = self.max_split
        n = len(s)

        for i in xrange(n):
            byte = mylib.ByteAt(s, i)

            if self.state == state_i.Backslash:
                pass

            elif (max_split >= 0 and self.state != state_i.Start and
                  len(self.args) >= max_split):
                # When max_split is reached, the processing is modified.
                if allow_escape and byte == pyos.BACKSLASH_CH:
                    self.max_split_trim = 0
                    self.state = state_i.Backslash
                    continue
                elif mylib.ByteInSet(byte, ifs_space):
                    self.max_split_trim += 1
                else:
                    self.max_split_trim = 0

            elif allow_escape and byte == pyos.BACKSLASH_CH:
                if self.state == state_i.White:
                    self._GenerateWord()
                self.state = state_i.Backslash
                continue
            elif mylib.ByteInSet(byte, ifs_space):
                if self.state != state_i.Start:
                    self.state = state_i.White
                continue
            elif mylib.ByteInSet(byte, ifs_other):
                self._GenerateWord()
                self.state = state_i.Start
                continue

            if self.state == state_i.White:
                self._GenerateWord()
            self.char_buff.append(byte)
            self.state = state_i.Black

    def PushTerminator(self):
        # type: () -> List[str]
        if self.state in (state_i.White, state_i.Black):
            self._GenerateWord()
            self.state = state_i.Start
        return self.args

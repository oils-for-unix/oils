"""comp_ui.py."""
from __future__ import print_function

from core import ansi
from core import completion
import libc

from mycpp import mylib

from typing import Any, List, Optional, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend.py_readline import Readline
    from core.util import _DebugFile
    from core import pyos

# ANSI escape codes affect the prompt!
# https://superuser.com/questions/301353/escape-non-printing-characters-in-a-function-for-a-bash-prompt
#
# Readline understands \x01 and \x02, while bash understands \[ and \].

# NOTE: There were used in demoish.py.  Do we still want those styles?
if 0:
    PROMPT_BOLD = '\x01%s\x02' % ansi.BOLD
    PROMPT_RESET = '\x01%s\x02' % ansi.RESET
    PROMPT_UNDERLINE = '\x01%s\x02' % ansi.UNDERLINE
    PROMPT_REVERSE = '\x01%s\x02' % ansi.REVERSE


def _PromptLen(prompt_str):
    # type: (str) -> int
    """Ignore all characters between \x01 and \x02 and handle unicode
    characters.

    In particular, the display width of a string may be different from
    either the number of bytes or the number of unicode characters.
    Additionally, if there are multiple lines in the prompt, only give
    the length of the last line.
    """
    escaped = False
    display_str = ""
    for c in prompt_str:
        if c == '\x01':
            escaped = True
        elif c == '\x02':
            escaped = False
        elif not escaped:
            # mycpp: rewrite of +=
            display_str = display_str + c
    last_line = display_str.split('\n')[-1]
    try:
        width = libc.wcswidth(last_line)
    # en_US.UTF-8 locale missing, just return the number of bytes
    except UnicodeError:
        return len(display_str)
    if width == -1:
        return len(display_str)
    return width


class PromptState(object):
    """For the InteractiveLineReader to communicate with the Display
    callback."""

    def __init__(self):
        # type: () -> None
        self.last_prompt_str = None  # type: Optional[str]
        self.last_prompt_len = -1

    def SetLastPrompt(self, prompt_str):
        # type: (str) -> None
        self.last_prompt_str = prompt_str
        self.last_prompt_len = _PromptLen(prompt_str)


class State(object):
    """For the RootCompleter to communicate with the Display callback."""

    def __init__(self):
        # type: () -> None
        # original line, truncated
        self.line_until_tab = None  # type: Optional[str]

        # Start offset in EVERY candidate to display.  We send fully-completed
        # LINES to readline because we don't want it to do its own word splitting.
        self.display_pos = -1

        # completion candidate descriptions
        self.descriptions = {}  # type: Dict[str, str]


class _IDisplay(object):
    """Interface for completion displays."""

    def __init__(self, comp_state, prompt_state, num_lines_cap, f, debug_f):
        # type: (State, PromptState, int, mylib.Writer, _DebugFile) -> None
        self.comp_state = comp_state
        self.prompt_state = prompt_state
        self.num_lines_cap = num_lines_cap
        self.f = f
        self.debug_f = debug_f

    def PrintCandidates(self, unused_subst, matches, unused_match_len):
        # type: (Optional[str], List[str], int) -> None
        try:
            self._PrintCandidates(unused_subst, matches, unused_match_len)
        except Exception:
            if 0:
                import traceback
                traceback.print_exc()

    def _PrintCandidates(self, unused_subst, matches, unused_match_len):
        # type: (Optional[str], List[str], int) -> None
        """Abstract method."""
        raise NotImplementedError()

    def Reset(self):
        # type: () -> None
        """Call this in between commands."""
        pass

    def ShowPromptOnRight(self, rendered):
        # type: (str) -> None
        # Doesn't apply to MinimalDisplay
        pass

    def EraseLines(self):
        # type: () -> None
        # Doesn't apply to MinimalDisplay
        pass

    if mylib.PYTHON:

        def PrintRequired(self, msg, *args):
            # type: (str, *Any) -> None
            # This gets called with "nothing to display"
            pass

        def PrintOptional(self, msg, *args):
            # type: (str, *Any) -> None
            pass


class MinimalDisplay(_IDisplay):
    """A display with minimal dependencies.

    It doesn't output color or depend on the terminal width. It could be
    useful if we ever have a browser build!  We can see completion
    without testing it.
    """

    def __init__(self, comp_state, prompt_state, debug_f):
        # type: (State, PromptState, _DebugFile) -> None
        _IDisplay.__init__(self, comp_state, prompt_state, 10, mylib.Stdout(),
                           debug_f)

        self.reader = None

    def _RedrawPrompt(self):
        # type: () -> None
        # NOTE: This has to reprint the prompt and the command line!
        # Like bash, we SAVE the prompt and print it, rather than re-evaluating it.
        self.f.write(self.prompt_state.last_prompt_str)
        self.f.write(self.comp_state.line_until_tab)

    def _PrintCandidates(self, unused_subst, matches, unused_match_len):
        # type: (Optional[str], List[str], int) -> None
        #log('_PrintCandidates %s', matches)
        self.f.write('\n')  # need this
        display_pos = self.comp_state.display_pos
        assert display_pos != -1

        too_many = False
        i = 0
        for m in matches:
            self.f.write(' %s\n' % m[display_pos:])

            if i == self.num_lines_cap:
                too_many = True
                i += 1  # Count this one
                break

            i += 1

        if too_many:
            num_left = len(matches) - i
            if num_left:
                self.f.write(' ... and %d more\n' % num_left)

        self._RedrawPrompt()

    if mylib.PYTHON:

        def PrintRequired(self, msg, *args):
            # type: (str, *Any) -> None
            self.f.write('\n')
            if args:
                msg = msg % args
            self.f.write(' %s\n' % msg)  # need a newline
            self._RedrawPrompt()


def _PrintPacked(matches, max_match_len, term_width, max_lines, f):
    # type: (List[str], int, int, int, mylib.Writer) -> int
    # With of each candidate.  2 spaces between each.
    w = max_match_len + 2

    # Number of candidates per line.  Don't print in first or last column.
    num_per_line = max(1, (term_width - 2) // w)

    fmt = '%-' + str(w) + 's'
    num_lines = 0

    too_many = False
    remainder = num_per_line - 1
    i = 0  # num matches
    for m in matches:
        if i % num_per_line == 0:
            f.write(' ')  # 1 space left gutter

        f.write(fmt % m)

        if i % num_per_line == remainder:
            f.write('\n')  # newline (leaving 1 space right gutter)
            num_lines += 1

            # Check if we've printed enough lines
            if num_lines == max_lines:
                too_many = True
                i += 1  # count this one
                break
        i += 1

    # Write last line break, unless it came out exactly.
    if i % num_per_line != 0:
        #log('i = %d, num_per_line = %d, i %% num_per_line = %d',
        #    i, num_per_line, i % num_per_line)

        f.write('\n')
        num_lines += 1

    if too_many:
        # TODO: Save this in the Display class
        fmt2 = ansi.BOLD + ansi.BLUE + '%' + str(term_width -
                                                 2) + 's' + ansi.RESET
        num_left = len(matches) - i
        if num_left:
            f.write(fmt2 % '... and %d more\n' % num_left)
            num_lines += 1

    return num_lines


def _PrintLong(
        matches,  # type: List[str]
        max_match_len,  # type: int
        term_width,  # type: int
        max_lines,  # type: int
        descriptions,  # type: Dict[str, str]
        f,  # type: mylib.Writer
):
    # type: (...) -> int
    """Print flags with descriptions, one per line.

    Args:
      descriptions: dict of { prefix-stripped match -> description }

    Returns:
      The number of lines printed.
    """
    #log('desc = %s', descriptions)

    # Subtract 3 chars: 1 for left and right margin, and then 1 for the space in
    # between.
    max_desc = max(0, term_width - max_match_len - 3)
    fmt = ' %-' + str(
        max_match_len) + 's ' + ansi.YELLOW + '%s' + ansi.RESET + '\n'

    num_lines = 0

    # rl_match is a raw string, which may or may not have a trailing space
    for rl_match in matches:
        desc = descriptions.get(rl_match)
        if desc is None:
            desc = ''
        if max_desc == 0:  # the window is not wide enough for some flag
            f.write(' %s\n' % rl_match)
        else:
            if len(desc) > max_desc:
                desc = desc[:max_desc - 5] + ' ... '
            f.write(fmt % (rl_match, desc))

        num_lines += 1

        if num_lines == max_lines:
            # right justify
            fmt2 = ansi.BOLD + ansi.BLUE + '%' + str(term_width -
                                                     1) + 's' + ansi.RESET
            num_left = len(matches) - num_lines
            if num_left:
                f.write(fmt2 % '... and %d more\n' % num_left)
                num_lines += 1
            break

    return num_lines


class NiceDisplay(_IDisplay):
    """Methods to display completion candidates and other messages.

    This object has to remember how many lines we last drew, in order to erase
    them before drawing something new.

    It's also useful for:
    - Stripping off the common prefix according to OUR rules, not readline's.
    - displaying descriptions of flags and builtins
    """

    def __init__(
            self,
            term_width,  # type: int
            comp_state,  # type: State
            prompt_state,  # type: PromptState
            debug_f,  # type: _DebugFile
            readline,  # type: Optional[Readline]
            signal_safe,  # type: pyos.SignalSafe
    ):
        # type: (...) -> None
        """
    Args:
      bold_line: Should user's entry be bold?
    """
        _IDisplay.__init__(self, comp_state, prompt_state, 10, mylib.Stdout(),
                           debug_f)

        self.term_width = term_width  # initial terminal width; will be invalidated

        self.readline = readline
        self.signal_safe = signal_safe

        self.bold_line = False

        self.num_lines_last_displayed = 0

        # For debugging only, could get rid of
        self.c_count = 0
        self.m_count = 0

        # hash of matches -> count.  Has exactly ONE entry at a time.
        self.dupes = {}  # type: Dict[int, int]

    def Reset(self):
        # type: () -> None
        """Call this in between commands."""
        self.num_lines_last_displayed = 0
        self.dupes.clear()

    def _ReturnToPrompt(self, num_lines):
        # type: (int) -> None
        # NOTE: We can't use ANSI terminal codes to save and restore the prompt,
        # because the screen may have scrolled.  Instead we have to keep track of
        # how many lines we printed and the original column of the cursor.

        orig_len = len(self.comp_state.line_until_tab)

        self.f.write('\x1b[%dA' % num_lines)  # UP
        last_prompt_len = self.prompt_state.last_prompt_len
        assert last_prompt_len != -1

        # Go right, but not more than the terminal width.
        n = orig_len + last_prompt_len
        n = n % self._GetTerminalWidth()
        self.f.write('\x1b[%dC' % n)  # RIGHT

        if self.bold_line:
            self.f.write(ansi.BOLD)  # Experiment

        self.f.flush()

    def _PrintCandidates(self, unused_subst, matches, unused_max_match_len):
        # type: (Optional[str], List[str], int) -> None
        term_width = self._GetTerminalWidth()

        # Variables set by the completion generator.  They should always exist,
        # because we can't get "matches" without calling that function.
        display_pos = self.comp_state.display_pos
        self.debug_f.write('DISPLAY POS in _PrintCandidates = %d\n' %
                           display_pos)

        self.f.write('\n')

        self.EraseLines()  # Delete previous completions!
        #log('_PrintCandidates %r', unused_subst, file=DEBUG_F)

        # Figure out if the user hit TAB multiple times to show more matches.
        # It's not correct to hash the line itself, because two different lines can
        # have the same completions:
        #
        # ls <TAB>
        # ls --<TAB>
        #
        # This is because there is a common prefix.
        # So instead use the hash of all matches as the identity.

        # This could be more accurate but I think it's good enough.
        comp_id = hash(''.join(matches))
        if comp_id in self.dupes:
            # mycpp: rewrite of +=
            self.dupes[comp_id] = self.dupes[comp_id] + 1
        else:
            self.dupes.clear()  # delete the old ones
            self.dupes[comp_id] = 1

        max_lines = self.num_lines_cap * self.dupes[comp_id]

        assert display_pos != -1
        if display_pos == 0:  # slight optimization for first word
            to_display = matches
        else:
            to_display = [m[display_pos:] for m in matches]

        # Calculate max length after stripping prefix.
        lens = [len(m) for m in to_display]
        max_match_len = max(lens)

        # TODO: NiceDisplay should truncate when max_match_len > term_width?
        # Also truncate when a single candidate is super long?

        # Print and go back up.  But we have to ERASE these before hitting enter!
        if self.comp_state.descriptions is not None and len(
                self.comp_state.descriptions) > 0:  # exists and is NON EMPTY
            num_lines = _PrintLong(to_display, max_match_len, term_width,
                                   max_lines, self.comp_state.descriptions,
                                   self.f)
        else:
            num_lines = _PrintPacked(to_display, max_match_len, term_width,
                                     max_lines, self.f)

        self._ReturnToPrompt(num_lines + 1)
        self.num_lines_last_displayed = num_lines

        self.c_count += 1

    if mylib.PYTHON:

        def PrintRequired(self, msg, *args):
            # type: (str, *Any) -> None
            """Print a message below the prompt, and then return to the
            location on the prompt line."""
            if args:
                msg = msg % args

            # This will mess up formatting
            assert not msg.endswith('\n'), msg

            self.f.write('\n')

            self.EraseLines()
            #log('PrintOptional %r', msg, file=DEBUG_F)

            # Truncate to terminal width
            max_len = self._GetTerminalWidth() - 2
            if len(msg) > max_len:
                msg = msg[:max_len - 5] + ' ... '

            # NOTE: \n at end is REQUIRED.  Otherwise we get drawing problems when on
            # the last line.
            fmt = ansi.BOLD + ansi.BLUE + '%' + str(
                max_len) + 's' + ansi.RESET + '\n'
            self.f.write(fmt % msg)

            self._ReturnToPrompt(2)

            self.num_lines_last_displayed = 1
            self.m_count += 1

        def PrintOptional(self, msg, *args):
            # type: (str, *Any) -> None
            self.PrintRequired(msg, *args)

    def ShowPromptOnRight(self, rendered):
        # type: (str) -> None
        n = self._GetTerminalWidth() - 2 - len(rendered)
        spaces = ' ' * n

        # We avoid drawing problems if we print it on its own line:
        # - inserting text doesn't push it to the right
        # - you can't overwrite it
        self.f.write(spaces + ansi.REVERSE + ' ' + rendered + ' ' + ansi.RESET +
                     '\r\n')

    def EraseLines(self):
        # type: () -> None
        """Clear N lines one-by-one.

        Assume the cursor is right below thep rompt:

        ish$ echo hi
        _ <-- HERE

        That's the first line to erase out of N.  After erasing them, return it
        there.
        """
        if self.bold_line:
            self.f.write(ansi.RESET)  # if command is bold
            self.f.flush()

        n = self.num_lines_last_displayed

        #log('EraseLines %d (c = %d, m = %d)', n, self.c_count, self.m_count,
        #    file=DEBUG_F)

        if n == 0:
            return

        for i in xrange(n):
            self.f.write('\x1b[2K')  # 2K clears entire line (not 0K or 1K)
            self.f.write('\x1b[1B')  # go down one line

        # Now go back up
        self.f.write('\x1b[%dA' % n)
        self.f.flush()  # Without this, output will look messed up

    def _GetTerminalWidth(self):
        # type: () -> int
        if self.signal_safe.PollSigWinch():  # is our value dirty?
            try:
                self.term_width = libc.get_terminal_width()
            except (IOError, OSError):
                # This shouldn't raise IOError because we did it at startup!  Under
                # rare circumstances stdin can change, e.g. if you do exec <&
                # input.txt.  So we have a fallback.
                self.term_width = 80
        return self.term_width


def ExecutePrintCandidates(display, sub, matches, max_len):
    # type: (_IDisplay, str, List[str], int) -> None
    display.PrintCandidates(sub, matches, max_len)


def InitReadline(
        readline,  # type: Optional[Readline]
        hist_file,  # type: Optional[str]
        root_comp,  # type: completion.RootCompleter
        display,  # type: _IDisplay
        debug_f,  # type: _DebugFile
):
    # type: (...) -> None
    assert readline

    if hist_file is not None:
        try:
            readline.read_history_file(hist_file)
        except (IOError, OSError):
            pass

    readline.parse_and_bind('tab: complete')

    readline.parse_and_bind('set horizontal-scroll-mode on')

    # How does this map to C?
    # https://cnswww.cns.cwru.edu/php/chet/readline/readline.html#SEC45

    complete_cb = completion.ReadlineCallback(readline, root_comp, debug_f)
    readline.set_completer(complete_cb)

    # http://web.mit.edu/gnu/doc/html/rlman_2.html#SEC39
    # "The basic list of characters that signal a break between words for the
    # completer routine. The default value of this variable is the characters
    # which break words for completion in Bash, i.e., " \t\n\"\\'`@$><=;|&{(""

    # This determines the boundaries you get back from get_begidx() and
    # get_endidx() at completion time!
    # We could be more conservative and set it to ' ', but then cases like
    # 'ls|w<TAB>' would try to complete the whole thing, instead of just 'w'.
    #
    # Note that this should not affect the OSH completion algorithm.  It only
    # affects what we pass back to readline and what readline displays to the
    # user!

    # No delimiters because readline isn't smart enough to tokenize shell!
    readline.set_completer_delims('')

    readline.set_completion_display_matches_hook(display)

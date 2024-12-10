"""
py_readline.py: GNU readline wrapper that's also implemented in C++
"""

try:
    import line_input
except ImportError:
    # Note: build/ovm-compile.sh doesn't build pyext/line_input.c unless shell
    # var $HAVE_READLINE is set
    # On the other hand, cpp/frontend_pyreadline.cc uses -D HAVE_READLINE, a
    # C++ preprocessor var
    line_input = None

from typing import Optional, Callable, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
    from core.completion import ReadlineCallback
    from core.comp_ui import _IDisplay


class Readline(object):
    """A thin wrapper around GNU readline to make it usable from C++."""

    def __init__(self):
        # type: () -> None
        assert line_input is not None

    def prompt_input(self, prompt):
        # type: (str) -> str
        """
        Print prompt, read line, and return it with trailing newline.  Or raise
        EOFError.
        """
        # Add trailing newline to make GNU readline conform to Python's
        # f.readline() interface
        return raw_input(prompt) + '\n'

    def parse_and_bind(self, s):
        # type: (str) -> None
        line_input.parse_and_bind(s)

    def read_init_file(self, s):
        # type: (str) -> None
        line_input.read_init_file(s)

    def add_history(self, line):
        # type: (str) -> None
        line_input.add_history(line)

    def read_history_file(self, path=None):
        # type: (Optional[str]) -> None
        line_input.read_history_file(path)

    def write_history_file(self, path=None):
        # type: (Optional[str]) -> None
        line_input.write_history_file(path)

    def set_completer(self, completer=None):
        # type: (Optional[ReadlineCallback]) -> None
        line_input.set_completer(completer)

    def set_completer_delims(self, delims):
        # type: (str) -> None
        line_input.set_completer_delims(delims)

    def set_completion_display_matches_hook(self, display=None):
        # type: (Optional[_IDisplay]) -> None
        hook = None
        if display is not None:
            hook = lambda *args: display.PrintCandidates(*args)

        line_input.set_completion_display_matches_hook(hook)

    def get_line_buffer(self):
        # type: () -> str
        return line_input.get_line_buffer()

    def get_begidx(self):
        # type: () -> int
        return line_input.get_begidx()

    def get_endidx(self):
        # type: () -> int
        return line_input.get_endidx()

    def clear_history(self):
        # type: () -> None
        line_input.clear_history()

    def get_history_item(self, pos):
        # type: (int) -> str
        return line_input.get_history_item(pos)

    def remove_history_item(self, pos):
        # type: (int) -> None
        line_input.remove_history_item(pos)

    def get_current_history_length(self):
        # type: () -> int
        return line_input.get_current_history_length()

    def resize_terminal(self):
        # type: () -> None
        line_input.resize_terminal()

    def list_funmap_names(self):
        # type: () -> None
        line_input.list_funmap_names()

    def function_dumper(self, print_readably):
        # type: (bool) -> None
        line_input.function_dumper(print_readably)

    def macro_dumper(self, print_readably):
        # type: (bool) -> None
        line_input.macro_dumper(print_readably)

    def variable_dumper(self, print_readably):
        # type: (bool) -> None
        line_input.variable_dumper(print_readably)

    def query_bindings(self, fn_name):
        # type: (str) -> None
        line_input.query_bindings(fn_name)

    def unbind_rl_function(self, fn_name):
        # type: (str) -> None
        line_input.unbind_rl_function(fn_name)

    def use_temp_keymap(self, fn_name):
        # type: (str) -> None
        line_input.use_temp_keymap(fn_name)

    def restore_orig_keymap(self):
        # type: () -> None
        line_input.restore_orig_keymap()

    def print_shell_cmd_map(self):
        # type: () -> None
        line_input.print_shell_cmd_map()

    def unbind_keyseq(self, keyseq):
        # type: (str) -> None
        line_input.unbind_keyseq(keyseq)

    def bind_shell_command(self, bindseq):
        # type: (str) -> None
        cmdseq_split = bindseq.strip().split(":", 1)
        if len(cmdseq_split) != 2:
            raise ValueError("%s: missing colon separator" % bindseq)

        # Below checks prevent need to do so in C, but also ensure rl_generic_bind
        # will not try to incorrectly xfree `cmd`/`data`, which doesn't belong to it
        keyseq = cmdseq_split[0].rstrip()
        if len(keyseq) <= 2:
            raise ValueError("%s: empty/invalid key sequence" % keyseq)
        if keyseq[0] != '"' or keyseq[-1] != '"':
            raise ValueError(
                "%s: missing double-quotes around the key sequence" % keyseq)
        keyseq = keyseq[1:-1]

        cmd = cmdseq_split[1]
        line_input.bind_shell_command(keyseq, cmd)

    def set_bind_shell_command_hook(self, hook):
        # type: (Callable[[str, str, int], Tuple[int, str, str]]) -> None

        if hook is None:
            raise ValueError("missing bind shell command hook function")

        line_input.set_bind_shell_command_hook(hook)


def MaybeGetReadline():
    # type: () -> Optional[Readline]
    """Returns a readline "module" if we were built with readline support."""
    if line_input is not None:
        return Readline()

    return None


if __name__ == '__main__':
    import sys
    readline = MaybeGetReadline()
    try:
        prompt_str = sys.argv[1]
    except IndexError:
        prompt_str = '! '

    while True:
        x = readline.prompt_input(prompt_str)
        print(x)

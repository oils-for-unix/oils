from typing import Callable, List, Optional, Tuple


def parse_and_bind(s: str) -> None: ...

def read_init_file(s: str) -> None: ...

def add_history(line: str) -> None: ...

def read_history_file(path: Optional[str] = None) -> None: ...

def write_history_file(path: Optional[str] = None) -> None: ...

def set_completer(completer: Optional[Callable[[str, int], str]] = None) -> None: ...

def set_completer_delims(delims: str) -> None: ...

def set_completion_display_matches_hook(hook: Optional[Callable[[str, List[str], int], None]] = None) -> None: ...

def get_line_buffer() -> str: ...

def get_begidx() -> int: ...

def get_endidx() -> int: ...

def clear_history() -> None: ...

def get_history_item(pos: int) -> str: ...

def remove_history_item(pos: int) -> None: ...

def get_current_history_length() -> int: ...

def resize_terminal() -> None: ...

def list_funmap_names() -> None: ...

def function_dumper(print_readably: bool) -> None: ...

def macro_dumper(print_readably: bool) -> None: ...

def variable_dumper(print_readably: bool) -> None: ...

def query_bindings(fn_name: str) -> None: ...

def unbind_rl_function(fn_name: str) -> None: ...

def use_temp_keymap(keymap_name: str) -> None: ...

def restore_orig_keymap() -> None: ...

def print_shell_cmd_map() -> None: ...

def unbind_keyseq(keyseq: str) -> None: ...

def bind_shell_command(keyseq: str, cmd: str) -> None: ...

def set_bind_shell_command_hook(hook: Callable[[str, str, int], Tuple[int, str, str]]) -> None: ...

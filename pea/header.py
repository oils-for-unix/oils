from dataclasses import dataclass
import ast
from ast import AST, Module, ClassDef, FunctionDef, Assign
from pprint import pprint
import sys

from typing import Any

from mycpp import pass_state


def log(msg: str, *args: Any) -> None:
    if args:
        msg = msg % args
    #print('%.2f %s' % (time.time() - START_TIME, msg), file=sys.stderr)
    print(msg, file=sys.stderr)


@dataclass
class PyFile:
    filename: str
    namespace: str  # C++ namespace
    module: ast.Module  # parsed representation


class Program:
    """A program is a collection of PyFiles."""

    def __init__(self) -> None:
        self.py_files: list[PyFile] = []

        # As we parse, we add modules, and fill in the dictionaries with parsed
        # types.  Then other passes can retrieve the types with the same
        # dictionaries.

        # right now types are modules?  Could change that
        self.func_types: dict[FunctionDef, AST] = {}
        self.method_types: dict[FunctionDef, AST] = {}
        self.class_types: dict[ClassDef, Module] = {}
        self.assign_types: dict[Assign, Module] = {}

        # like mycpp: type and variable string.  TODO: We shouldn't flatten it to a
        # C type until later.
        #
        # Note: ImplPass parses the types.  So I guess this could be limited to
        # that?
        # DoFunctionMethod() could make two passes?
        # 1. collect vars
        # 2. print code

        self.local_vars: dict[FunctionDef, list[tuple[str, str]]] = {}

        # ForwardDeclPass:
        #   OnMethod()
        #   OnSubclass()

        # Then
        # Calculate()
        #
        # PrototypesPass: # IsVirtual
        self.virtual = pass_state.Virtual()

        self.stats: dict[str, int] = {
            # parsing stats
            'num_files': 0,
            'num_funcs': 0,
            'num_classes': 0,
            'num_methods': 0,
            'num_assign': 0,

            # ConstPass stats
            'num_strings': 0,
        }

    def PrintStats(self) -> None:
        pprint(self.stats, stream=sys.stderr)
        print('', file=sys.stderr)


class TypeSyntaxError(Exception):

    def __init__(self, lineno: int, code_str: str):
        self.lineno = lineno
        self.code_str = code_str

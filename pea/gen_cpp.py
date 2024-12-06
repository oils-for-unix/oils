import ast
from ast import AST, stmt, ClassDef, FunctionDef, Assign

import typing
from typing import Any

from pea.header import (TypeSyntaxError, PyFile, Program)


def _ParseFuncType(st: stmt) -> AST:
    # 2024-12: causes an error with the latest MyPy, 1.13.0
    #          works with Soil CI MyPy, 1.10.0
    #assert st.type_comment, st

    # Caller checks this.   Is there a better way?
    assert hasattr(st, 'type_comment'), st

    try:
        # This parses with the func_type production in the grammar
        return ast.parse(st.type_comment, mode='func_type')
    except SyntaxError:
        raise TypeSyntaxError(st.lineno, st.type_comment)


class ConstVisitor(ast.NodeVisitor):

    def __init__(self, const_lookup: dict[str, int]):
        ast.NodeVisitor.__init__(self)
        self.const_lookup = const_lookup
        self.str_id = 0

    def visit_Constant(self, o: ast.Constant) -> None:
        if isinstance(o.value, str):
            self.const_lookup[o.value] = self.str_id
            self.str_id += 1


class ForwardDeclPass:
    """Emit forward declarations."""

    # TODO: Move this to ParsePass after comparing with mycpp.

    def __init__(self, f: typing.IO[str]) -> None:
        self.f = f

    def DoPyFile(self, py_file: PyFile) -> None:

        # TODO: could omit empty namespaces
        namespace = py_file.namespace
        self.f.write(f'namespace {namespace} {{  // forward declare\n')

        for stmt in py_file.module.body:
            match stmt:
                case ClassDef():
                    class_name = stmt.name
                    self.f.write(f'  class {class_name};\n')

        self.f.write(f'}}  // forward declare {namespace}\n')
        self.f.write('\n')


class PrototypesPass:
    """Parse signatures and Emit function prototypes."""

    def __init__(self, opts: Any, prog: Program, f: typing.IO[str]) -> None:
        self.opts = opts
        self.prog = prog
        self.f = f

    def DoClass(self, cls: ClassDef) -> None:
        for stmt in cls.body:
            match stmt:
                case FunctionDef():
                    if stmt.type_comment:
                        sig = _ParseFuncType(stmt)  # may raise

                        if self.opts.verbose:
                            print('METHOD')
                            print(ast.dump(sig, indent='  '))
                            # TODO: We need to print virtual here

                        self.prog.method_types[stmt] = sig  # save for ImplPass
                    self.prog.stats['num_methods'] += 1

                # TODO: assert that there aren't top-level statements?
                case _:
                    pass

    def DoPyFile(self, py_file: PyFile) -> None:
        for stmt in py_file.module.body:
            match stmt:
                case FunctionDef():
                    if stmt.type_comment:
                        sig = _ParseFuncType(stmt)  # may raise

                        if self.opts.verbose:
                            print('FUNC')
                            print(ast.dump(sig, indent='  '))

                        self.prog.func_types[stmt] = sig  # save for ImplPass

                    self.prog.stats['num_funcs'] += 1

                case ClassDef():
                    self.DoClass(stmt)
                    self.prog.stats['num_classes'] += 1

                case _:
                    # Import, Assign, etc.
                    #print(stmt)

                    # TODO: omit __name__ == '__main__' etc.
                    # if __name__ == '__main__'
                    pass


class ImplPass:
    """Emit function and method bodies.

    Algorithm:
      collect local variables first
    """

    def __init__(self, prog: Program, f: typing.IO[str]) -> None:
        self.prog = prog
        self.f = f

    # TODO: needs to be fully recursive, so you get bodies of loops, etc.
    def DoBlock(self, stmts: list[stmt], indent: int = 0) -> None:
        """e.g. body of function, method, etc."""

        #print('STMTS %s' % stmts)

        ind_str = '  ' * indent

        for stmt in stmts:
            match stmt:
                case Assign():
                    #print('%s* Assign' % ind_str)
                    #print(ast.dump(stmt, indent='  '))

                    if stmt.type_comment:
                        # This parses with the func_type production in the grammar
                        try:
                            typ = ast.parse(stmt.type_comment)
                        except SyntaxError as e:
                            # New syntax error
                            raise TypeSyntaxError(stmt.lineno,
                                                  stmt.type_comment)

                        self.prog.assign_types[stmt] = typ

                        #print('%s  TYPE: Assign' % ind_str)
                        #print(ast.dump(typ, indent='  '))

                    self.prog.stats['num_assign'] += 1

                case _:
                    pass

    def DoClass(self, cls: ClassDef) -> None:
        for stmt in cls.body:
            match stmt:
                case FunctionDef():
                    self.DoBlock(stmt.body, indent=1)

                case _:
                    pass

    def DoPyFile(self, py_file: PyFile) -> None:
        for stmt in py_file.module.body:
            match stmt:
                case ClassDef():
                    self.DoClass(stmt)

                case FunctionDef():
                    self.DoBlock(stmt.body, indent=1)

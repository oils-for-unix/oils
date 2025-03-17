import ast
from ast import AST, stmt
import os

from pea.header import TypeSyntaxError, Program, PyFile


def ParseFuncType(st: stmt) -> AST:
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


def ParseFiles(files: list[str], prog: Program) -> bool:

    for filename in files:
        with open(filename) as f:
            contents = f.read()

        try:
            # Python 3.8+ supports type_comments=True
            module = ast.parse(contents, filename=filename, type_comments=True)
        except SyntaxError as e:
            # This raises an exception for some reason
            #e.print_file_and_line()
            print('Error parsing %s: %s' % (filename, e))
            return False

        tmp = os.path.basename(filename)
        namespace, _ = os.path.splitext(tmp)

        prog.py_files.append(PyFile(filename, namespace, module))

        prog.stats['num_files'] += 1

    return True

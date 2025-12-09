"""
const_pass.py - AST pass that collects string constants.

Instead of emitting a dynamic allocation StrFromC("foo"), we emit a
GLOBAL_STR(str99, "foo"), and then a reference to str99.
"""
import collections
import json
import hashlib
import string

from mypy.nodes import (Expression, StrExpr, CallExpr, FuncDef, ClassDef,
                        MypyFile)
from mypy.types import Type

from mycpp import format_strings
from mycpp import util
from mycpp.util import log
from mycpp import visitor

from typing import Dict, List, Tuple, Counter, TextIO, Union, Optional

_ = log

_ALPHABET = string.ascii_lowercase + string.ascii_uppercase
_ALPHABET = _ALPHABET[:32]

AllStrings = Dict[Union[int, StrExpr], str]  # Node -> raw string
UniqueStrings = Dict[bytes, str]  # SHA1 digest -> raw string
HashedStrings = Dict[str, List[str]]  # short hash -> raw string
VarNames = Dict[str, str]  # raw string -> variable name

MethodDefinitions = Dict[util.SymbolPath,
                         List[str]]  # Class name -> List of method names

ClassNamespaceDict = Dict[util.SymbolPath, str]  # Class name -> Namespace name


class GlobalStrings:

    def __init__(self) -> None:
        # SHA1 hash -> encoded bytes
        self.all_strings: AllStrings = {}
        self.var_names: VarNames = {}

        # OLD
        self.unique: Dict[bytes, bytes] = {}
        self.int_id_lookup: Dict[Expression, str] = {}
        self.pairs: List[Tuple[str, str]] = []

    def Add(self, key: Union[int, StrExpr], s: str) -> None:
        """
        key: int for tests
             StrExpr node for production
        """
        self.all_strings[key] = s

    def ComputeStableVarNames(self) -> None:
        unique = _MakeUniqueStrings(self.all_strings)
        hash15 = _HashAndCollect(unique)
        self.var_names = _HandleCollisions(hash15)

    def GetVarName(self, node: StrExpr) -> str:
        # StrExpr -> str -> variable names
        return self.var_names[self.all_strings[node]]

    def WriteConstants(self, out_f: TextIO) -> None:
        if util.SMALL_STR:
            macro_name = 'GLOBAL_STR2'
        else:
            macro_name = 'GLOBAL_STR'

        # sort by the string value itself
        for raw_string in sorted(self.var_names):
            var_name = self.var_names[raw_string]
            out_f.write('%s(%s, %s);\n' %
                        (macro_name, var_name, json.dumps(raw_string)))

        out_f.write('\n')


class MethodDefs:

    def __init__(self) -> None:
        self.method_defs: MethodDefinitions = {}

    def Add(self, class_name: util.SymbolPath, method_name: str) -> None:
        if class_name in self.method_defs:
            self.method_defs[class_name].append(method_name)
        else:
            self.method_defs[class_name] = [method_name]

    def ClassHasMethod(self, class_name: util.SymbolPath,
                       method_name: str) -> bool:
        return (class_name in self.method_defs and
                method_name in self.method_defs[class_name])


class ClassNamespaces:

    def __init__(self) -> None:
        self.class_namespaces: ClassNamespaceDict = {}

    def Set(self, class_name: util.SymbolPath, namespace_name: str) -> None:
        self.class_namespaces[class_name] = namespace_name

    def GetClassNamespace(self, class_name: util.SymbolPath) -> str:
        return self.class_namespaces[class_name]


class Collect(visitor.TypedVisitor):

    def __init__(self, types: Dict[Expression, Type],
                 global_strings: GlobalStrings, method_defs: MethodDefs,
                 class_namespaces: ClassNamespaces) -> None:
        visitor.TypedVisitor.__init__(self, types)
        self.global_strings = global_strings

        # Only generate unique strings.
        # Before this optimization, _gen/bin/oils_for_unix.mycpp.cc went up to:
        #     "str2824"
        # After:
        #     "str1789"
        #
        # So it saved over 1000 strings.
        #
        # The C++ compiler should also optimize it, but it's easy for us to
        # generate less source code.

        # unique string value -> id
        self.unique: Dict[str, str] = {}
        self.unique_id = 0

        self.method_defs = method_defs
        self.class_namespaces = class_namespaces

        self.current_file_name: Optional[str] = None

    def verify_format_string(self, fmt: StrExpr) -> None:
        try:
            format_strings.Parse(fmt.value)
        except RuntimeError as e:
            self.report_error(fmt, str(e))

    def oils_visit_format_expr(self, left: Expression,
                               right: Expression) -> None:
        if isinstance(left, StrExpr):
            self.verify_format_string(left)
            # Do NOT visit the left, because we write it literally
            pass
        else:
            self.accept(left)
        self.accept(right)

    def visit_str_expr(self, o: StrExpr) -> None:
        raw_string = format_strings.DecodeMyPyString(o.value)
        self.global_strings.Add(o, raw_string)

    def oils_visit_probe_call(self, o: CallExpr) -> None:
        # Don't generate constants for DTRACE_PROBE()
        pass

    def oils_visit_log_call(self, fmt: StrExpr,
                            args: List[Expression]) -> None:
        self.verify_format_string(fmt)
        if len(args) == 0:
            self.accept(fmt)
            return

        # Don't generate a string constant for the format string, which is an
        # inlined C string, not a mycpp GC string
        for i, arg in enumerate(args):
            self.accept(arg)

    def oils_visit_class_def(
            self, o: ClassDef, base_class_sym: Optional[util.SymbolPath],
            current_class_name: Optional[util.SymbolPath]) -> None:

        for stmt in o.defs.body:
            if isinstance(stmt, FuncDef):
                self.method_defs.Add(current_class_name, stmt.name)
                self.class_namespaces.Set(current_class_name,
                                          self.current_file_name)
        super().oils_visit_class_def(o, base_class_sym, current_class_name)

    def oils_visit_mypy_file(self, o: MypyFile) -> None:
        self.current_file_name = o.name
        super().oils_visit_mypy_file(o)


def _MakeUniqueStrings(all_strings: AllStrings) -> UniqueStrings:
    """
    Given all the strings, make a smaller set of unique strings.
    """
    unique: UniqueStrings = {}
    for _, raw_string in all_strings.items():
        b = raw_string.encode('utf-8')
        h = hashlib.sha1(b).digest()
        #print(repr(h))

        if h in unique:
            # extremely unlikely
            assert unique[h] == raw_string, ("SHA1 hash collision! %r and %r" %
                                             (unique[h], b))
        unique[h] = raw_string
    return unique


def _ShortHash15(h: bytes) -> str:
    """
    Given a SHA1, create a 15 bit hash value.

    We use three base-(2**5) aka base-32 digits, encoded as letters.
    """
    bits16 = h[0] | h[1] << 8

    assert 0 <= bits16 < 2**16, bits16

    # 5 least significant bits
    d1 = bits16 & 0b11111
    bits16 >>= 5
    d2 = bits16 & 0b11111
    bits16 >>= 5
    d3 = bits16 & 0b11111
    bits16 >>= 5

    return _ALPHABET[d1] + _ALPHABET[d2] + _ALPHABET[d3]


def _HashAndCollect(unique: UniqueStrings) -> HashedStrings:
    """
    Use the short hash.
    """
    hash15 = collections.defaultdict(list)
    for sha1, b in unique.items():
        short_hash = _ShortHash15(sha1)
        hash15[short_hash].append(b)
    return hash15


def _SummarizeCollisions(hash15: HashedStrings) -> None:
    collisions: Counter[int] = collections.Counter()
    for short_hash, strs in hash15.items():
        n = len(strs)
        #if n > 1:
        if 0:
            print(short_hash)
            print(strs)
        collisions[n] += 1

    log('%10s %s', 'COUNT', 'ITEM')
    for item, count in collisions.most_common():
        log('%10d %s', count, item)


def _HandleCollisions(hash15: HashedStrings) -> VarNames:
    var_names: VarNames = {}
    for short_hash, bytes_list in hash15.items():
        bytes_list.sort()  # stable order, will bump some of the strings
        for i, b in enumerate(bytes_list):
            if i == 0:
                var_names[b] = 'S_%s' % short_hash
            else:
                var_names[b] = 'S_%s_%d' % (short_hash, i)
    return var_names


def HashDemo() -> None:
    import sys

    # 5 bits
    #_ALPHABET = _ALPHABET.replace('l', 'Z')  # use a nicer one?
    log('alpha %r', _ALPHABET)

    global_strings = GlobalStrings()

    all_lines = sys.stdin.readlines()
    for i, line in enumerate(all_lines):
        global_strings.Add(i, line.strip())

    unique = _MakeUniqueStrings(global_strings.all_strings)
    hash15 = _HashAndCollect(unique)
    var_names = _HandleCollisions(hash15)

    if 0:
        for b, var_name in var_names.items():
            if var_name[-1].isdigit():
                log('%r %r', var_name, b)
            #log('%r %r', var_name, b)

    log('Unique %d' % len(unique))
    log('hash15 %d' % len(hash15))

    _SummarizeCollisions(hash15)


if __name__ == '__main__':
    HashDemo()

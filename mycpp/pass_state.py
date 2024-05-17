"""
pass_state.py
"""
from __future__ import print_function

import subprocess
import os

from collections import defaultdict
from typing import Optional

from mycpp.util import log

_ = log


class Virtual(object):
    """
  See unit test for example usage.
  """

    def __init__(self) -> None:
        self.methods: dict[str, list[str]] = defaultdict(list)
        self.subclasses: dict[str, list[str]] = defaultdict(list)
        self.virtuals: dict[tuple[str, str], Optional[tuple[str, str]]] = {}
        self.has_vtable: dict[str, bool] = {}
        self.can_reorder_fields: dict[str, bool] = {}

        # _Executor -> vm::_Executor
        self.base_class_unique: dict[str, str] = {}

    # These are called on the Forward Declare pass
    def OnMethod(self, class_name: str, method_name: str) -> None:
        #log('OnMethod %s %s', class_name, method_name)

        # __init__ and so forth don't count
        if method_name.startswith('__') and method_name.endswith('__'):
            return

        self.methods[class_name].append(method_name)

    def OnSubclass(self, base_class: str, subclass: str) -> None:
        if '::' in base_class:
            # Hack for
            #
            # class _Executor: pass
            #   versus
            # class MyExecutor(vm._Executor): pass
            base_key = base_class.split('::')[-1]

            # Fail if we have two base classes in different namespaces with the same
            # name.
            if base_key in self.base_class_unique:
                # Make sure we don't have collisions
                assert self.base_class_unique[base_key] == base_class or base_class in self.subclasses[self.base_class_unique[base_key]]
            else:
                self.base_class_unique[base_key] = base_class

        else:
            base_key = base_class

        self.subclasses[base_class].append(subclass)

    def Calculate(self) -> None:
        """
    Call this after the forward declare pass.

    TODO: Are there bugs based on conflicting class names?
    """
        for base_class, subclasses in self.subclasses.items():
            self.can_reorder_fields[base_class] = False

            for subclass in subclasses:
                self.can_reorder_fields[subclass] = False

                b_methods = self.methods[base_class]
                s_methods = self.methods[subclass]
                overlapping = set(b_methods) & set(s_methods)
                for method in overlapping:
                    self.virtuals[(base_class, method)] = None
                    self.virtuals[(subclass, method)] = (base_class, method)
                if overlapping:
                    self.has_vtable[base_class] = True
                    self.has_vtable[subclass] = True

    # These is called on the Decl pass
    def IsVirtual(self, class_name: str, method_name: str) -> bool:
        return (class_name, method_name) in self.virtuals

    def HasVTable(self, class_name: str) -> bool:
        return class_name in self.has_vtable

    def CanReorderFields(self, class_name: str) -> bool:
        if class_name in self.can_reorder_fields:
            return self.can_reorder_fields[class_name]
        else:
            return True  # by default they can be reordered


class CallGraph(object):

    def __init__(self) -> None:
        self.graph: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.mem: dict[tuple[str, str], Optional[str]] = {}

    def OnCall(self, caller: str, callee: str) -> None:
        self.graph[caller][callee] += 1

    def _Memoize(self, src: str, dst: str, next_hop: Optional[str]) -> bool:
        self.mem[(src, dst)] = next_hop
        return self.mem[(src, dst)] is not None

    def PathExists(self, src: str, dst: str) -> bool:

        def _dfs(u: str, v: str, visited: set[str]):
            if (u, v) in self.mem:
                return self.mem[(u, v)] is not None

            visited.add(u)
            if u not in self.graph:
                return False

            for neighbor in self.graph[u]:
                if neighbor == v:
                    return self._Memoize(u, v, neighbor)

                if neighbor not in visited and _dfs(neighbor, v, visited):
                    return self._Memoize(u, v, neighbor)

            return self._Memoize(u, v, None)

        if src == dst:
            return True

        found_path = _dfs(src, dst, set({}))

        # dump the path
        if 0:
            path = [src, self.mem[(src, dst)]]
            while path[-1] != dst:
                u = path[-1]
                for neighbor in self.graph[u]:
                    if self.mem[(u, dst)]:
                        path.append(self.mem[(u, dst)])
                        break

            print(src, dst)
            print(path)
            print('---')

        return found_path


def statement_name(statement_id):
    return 'S{}'.format(statement_id)


class LiveVars(object):

    def __init__(self) -> None:
        self.statements: dict[str, dict[int, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
        self.adj: dict[str, dict[int, dict[int, None]]] = defaultdict(lambda: defaultdict(dict))
        self.roots: dict[str, set[str]] = defaultdict(set)

    def EmitEdge(self, function: str, src_statement: int, dst_statement: int) -> None:
        self.adj[function][src_statement][dst_statement] = None

    def EmitDef(self, function: str, statement: int, var: str) -> None:
        self.statements[function][statement].append(('def', var))

    def EmitUse(self, function: str, statement: int, var: str) -> None:
        self.statements[function][statement].append(('use', var))

    def EmitCollect(self, function: str, statement: int) -> None:
        self.statements[function][statement].append(('collect', None))

    def DumpFunction(self, function: str, use_f, def_f, collect_f, graph_f) -> None:
        if function not in self.adj:
            return

        action_f = {'use': use_f, 'def': def_f}
        for u, neighbors in self.adj[function].items():
            for v in neighbors:
                graph_f.write('"%s"\t"%s"\t"%s"\n' % (function, statement_name(u),
                                                      statement_name(v)))


        for statement, statements in self.statements[function].items():
            for action, var in statements:
                if action == 'collect':
                    collect_f.write('"%s"\t"%s"\n' % (function, statement_name(statement)))
                else:
                    action_f[action].write('"%s"\t"%s"\t"%s"\n' %
                                           (function, statement_name(statement), var))


    def Compute(self):
        facts_dir = '_tmp/mycpp-facts'
        os.makedirs(facts_dir, exist_ok=True)
        use_facts = f'{facts_dir}/use.facts'
        def_facts = f'{facts_dir}/def.facts'
        collect_facts = f'{facts_dir}/collect.facts'
        cf_edge_facts = f'{facts_dir}/cf_edge.facts'
        with open(use_facts, 'w') as use_f, \
             open(def_facts, 'w') as def_f, \
             open(collect_facts, 'w') as collect_f, \
             open(cf_edge_facts, 'w') as graph_f:
            for func in self.statements:
                self.DumpFunction(func, use_f, def_f, collect_f, graph_f)

        subprocess.check_call(
            [
                '_bin/cxx-opt-Ivendor_std=c++17/mycpp/stack_roots',
                '-F', facts_dir,
                '-D', '_tmp',
            ]
        )
        with open('_tmp/root_vars.csv') as roots_f:
            for line in roots_f:
                line = line.rstrip().replace('"', '')
                function, variable = line.split('\t')
                self.roots[function].add(variable)

    def NeedsRoot(self, function: str, variable: str) -> bool:
        return function in self.roots and variable in self.roots[function]

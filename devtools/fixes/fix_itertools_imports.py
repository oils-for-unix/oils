""" Fixer for imports of itertools.(imap|ifilter|izip|ifilterfalse) """

# Local imports
from lib2to3 import fixer_base
from lib2to3 import pytree
from lib2to3.fixer_util import BlankLine, syms, token


# Unused: from fixes/fix_import.py
def traverse_imports(names):
    """
    Walks over all the names imported in a dotted_as_names node.
    """
    pending = [names]
    while pending:
        node = pending.pop()
        if node.type == token.NAME:
            yield node.value
        elif node.type == syms.dotted_name:
            yield "".join([ch.value for ch in node.children])
        elif node.type == syms.dotted_as_name:
            pending.append(node.children[0])
        elif node.type == syms.dotted_as_names:
            pending.extend(node.children[::-2])
        else:
            raise AssertionError("unknown node type")




class FixItertoolsImports(fixer_base.BaseFix):
    BM_compatible = True
    PATTERN = """
              import_from< 'from' imp=any 'import' ['('] imports=any [')'] >
              """ %(locals())

    def transform(self, node, results):
        #print('***')

        # lib2to3.pytree.Node
        #print('NODE %s' % type(node))

        imp = results['imp']
        if not isinstance(imp, pytree.Node):
            # filter out from X import Y
            return

        c0 = imp.children[0]
        if c0.value != '_devbuild':
            # Filter out
            return

        imports = results['imports']
        print()
        print('I %r' % imports)

        n = len(imports.children)
        to_remove = []
        for i, child in enumerate(imports.children):
            if child.value in ('value', 'value_e', 'value_t', 'value_str'):
                #print('NODE %r' % child)
                #print('NODE %r' % child.lineno)
                to_remove.append(child)

                # Remove any preceding comma
                if i < n-1:
                    after = imports.children[i+1]
                    print('after %r' % after)
                    if after.value == ',':
                        to_remove.append(after)

        for n in to_remove:
            imports.children.remove(n)

        # If there are no imports left, just get rid of the entire statement
        # copied from fix_itertools_imports.py
        if (not (imports.children or getattr(imports, 'value', None)) or
            imports.parent is None):
            p = node.prefix
            node = BlankLine()
            node.prefix = p
            return node

        if to_remove:
            return node

        return

        if imp == '_devbuild.gen.runtime_asdl':
            print('IMPORT %s %s' % (imp, imports))

        #raise AssertionError()
        return

        if imports.type == syms.import_as_name or not imports.children:
            children = [imports]
        else:
            children = imports.children
        for child in children[::2]:
            if child.type == token.NAME:
                member = child.value
                name_node = child
            elif child.type == token.STAR:
                # Just leave the import as is.
                return
            else:
                assert child.type == syms.import_as_name
                name_node = child.children[0]
            member_name = name_node.value
            if member_name in ('imap', 'izip', 'ifilter'):
                child.value = None
                child.remove()
            elif member_name in ('ifilterfalse', 'izip_longest'):
                node.changed()
                name_node.value = ('filterfalse' if member_name[1] == 'f'
                                   else 'zip_longest')

        # Make sure the import statement is still sane
        children = imports.children[:] or [imports]
        remove_comma = True
        for child in children:
            if remove_comma and child.type == token.COMMA:
                child.remove()
            else:
                remove_comma ^= True

        while children and children[-1].type == token.COMMA:
            children.pop().remove()

        # If there are no imports left, just get rid of the entire statement
        if (not (imports.children or getattr(imports, 'value', None)) or
            imports.parent is None):
            p = node.prefix
            node = BlankLine()
            node.prefix = p
            return node

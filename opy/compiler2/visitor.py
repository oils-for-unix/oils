
# XXX should probably rename ASTVisitor to ASTWalker
# XXX can it be made even more generic?

class ASTVisitor(object):
    """Performs a depth-first walk of the AST

    The ASTVisitor will walk the AST, performing either a preorder or
    postorder traversal depending on which method is called.

    methods:
    preorder(tree, visitor)
    postorder(tree, visitor)
        tree: an instance of ast.Node
        visitor: an instance with visitXXX methods

    The ASTVisitor is responsible for walking over the tree in the
    correct order.  For each node, it checks the visitor argument for
    a method named 'visitNodeType' where NodeType is the name of the
    node's class, e.g. Class.  If the method exists, it is called
    with the node as its sole argument.

    The visitor method for a particular node type can control how
    child nodes are visited during a preorder walk.  (It can't control
    the order during a postorder walk, because it is called _after_
    the walk has occurred.)  The ASTVisitor modifies the visitor
    argument by adding a visit method to the visitor; this method can
    be used to visit a child node of arbitrary type.
    """

    VERBOSE = 0

    def __init__(self):
        self._method_cache = {}

    def _Default(self, node, *args):
        """If a visitClassName method isn't provided, visit children."""
        for child in node.getChildNodes():
            self.Dispatch(child, *args)

    def Dispatch(self, node, *args):
        klass = node.__class__

        # TODO: Shouldn't it be keyed by string rather than class instance?
        # This would probably change the bytecode order.
        meth = self._method_cache.get(klass, None)
        if meth is None:
            className = klass.__name__
            meth = getattr(self, 'visit' + className, self._Default)
            self._method_cache[klass] = meth
        return meth(node, *args)

    # Subclasses call self.visit().  TODO: Rename?
    visit = Dispatch


class ExampleASTVisitor(ASTVisitor):
    """Prints examples of the nodes that aren't visited

    This visitor-driver is only useful for development, when it's
    helpful to develop a visitor incrementally, and get feedback on what
    you still have to do.
    """
    examples = {}

    def Dispatch(self, node, *args):
        self.node = node
        meth = self._method_cache.get(node.__class__, None)
        className = node.__class__.__name__
        if meth is None:
            meth = getattr(self.visitor, 'visit' + className, 0)
            self._method_cache[node.__class__] = meth
        if self.VERBOSE > 1:
            print("Dispatch", className, (meth and meth.__name__ or ''))
        if meth:
            meth(node, *args)
        elif self.VERBOSE > 0:
            klass = node.__class__
            if klass not in self.examples:
                self.examples[klass] = klass
                print()
                print(self.visitor)
                print(klass)
                for attr in dir(node):
                    if attr[0] != '_':
                        print("\t", "%-12.12s" % attr, getattr(node, attr))
                print()
            return self._Default(node, *args)

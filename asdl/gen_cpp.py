"""
gen_cpp.py - Generate C++ classes from an ASDL schema.

TODO:

- Integrate some of the lessons here:
  - https://github.com/oilshell/blog-code/tree/master/asdl
  - And maybe mycpp/target_lang.cc

- pretty printing methods
  - so asdl/format.py get translated?

- NoOp needs to be instantiated without args?
- dict becomes Dict[str, str] ?
- how to handle UserType(id) ?

- How do optional ASDL values like int? work?  Use C++ default values?
  - This means that all the optionals have to be on the end.  That seems OK.
  - I guess that's how Python does it.
"""
from __future__ import print_function

import sys

from collections import defaultdict

from asdl import ast
from asdl import visitor
from asdl.util import log

_ = log


# Used by core/asdl_gen.py to generate _devbuild/gen/osh-types.h, with
# lex_mode__*
class CEnumVisitor(visitor.AsdlVisitor):

    def VisitSimpleSum(self, sum, name, depth):
        # Just use #define, since enums aren't namespaced.
        for i, variant in enumerate(sum.types):
            self.Emit('#define %s__%s %d' % (name, variant.name, i + 1), depth)
        self.Emit("", depth)


_PRIMITIVES = {
    'string': 'BigStr*',  # declared in containers.h
    'int': 'int',
    'uint16': 'uint16_t',
    'BigInt': 'mops::BigInt',
    'float': 'double',
    'bool': 'bool',
    'any': 'void*',
    # TODO: frontend/syntax.asdl should properly import id enum instead of
    # hard-coding it here.
    'id': 'Id_t',
}


class ForwardDeclareVisitor(visitor.AsdlVisitor):
    """Print forward declarations.

    ASDL allows forward references of types, but C++ doesn't.
    """

    def VisitCompoundSum(self, sum, name, depth):
        self.Emit("class %(name)s_t;" % locals(), depth)

    def VisitProduct(self, product, name, depth):
        self.Emit("class %(name)s;" % locals(), depth)

    def EmitFooter(self):
        self.Emit("", 0)  # blank line


def _GetCppType(typ):
    if isinstance(typ, ast.ParameterizedType):
        type_name = typ.type_name

        if type_name == 'Dict':
            k_type = _GetCppType(typ.children[0])
            v_type = _GetCppType(typ.children[1])
            return 'Dict<%s, %s>*' % (k_type, v_type)

        elif type_name == 'List':
            c_type = _GetCppType(typ.children[0])
            return 'List<%s>*' % (c_type)

        elif type_name == 'Optional':
            c_type = _GetCppType(typ.children[0])
            return c_type

    elif isinstance(typ, ast.NamedType):

        if typ.resolved:
            if isinstance(typ.resolved, ast.SimpleSum):
                return '%s_t' % typ.name
            if isinstance(typ.resolved, ast.Sum):
                return '%s_t*' % typ.name
            if isinstance(typ.resolved, ast.Product):
                return '%s*' % typ.name
            if isinstance(typ.resolved, ast.Use):
                return '%s_asdl::%s*' % (typ.resolved.module_parts[-1],
                                         ast.TypeNameHeuristic(typ.name))
            if isinstance(typ.resolved, ast.Extern):
                r = typ.resolved
                type_name = r.names[-1]
                cpp_namespace = r.names[-2]
                return '%s::%s*' % (cpp_namespace, type_name)

        # 'id' falls through here
        return _PRIMITIVES[typ.name]

    else:
        raise AssertionError()


def _IsManagedType(typ):
    # This is a little cheesy, but works
    return _GetCppType(typ).endswith('*')


def _DefaultValue(typ, conditional=True):
    """Values that the ::CreateNull() constructor passes."""

    if isinstance(typ, ast.ParameterizedType):
        type_name = typ.type_name

        if type_name == 'Dict':  # TODO: can respect alloc_dicts=True
            return 'nullptr'

        elif type_name == 'List':
            c_type = _GetCppType(typ.children[0])

            d = 'Alloc<List<%s>>()' % (c_type)
            if conditional:
                return 'alloc_lists ? %s : nullptr' % d
            else:
                return d

        elif type_name == 'Optional':
            return 'nullptr'

        else:
            raise AssertionError(type_name)

    elif isinstance(typ, ast.NamedType):
        type_name = typ.name

        if type_name in ('int', 'uint16', 'BigInt'):
            default = '-1'
        elif type_name == 'id':  # hard-coded HACK
            default = '-1'
        elif type_name == 'bool':
            default = 'false'
        elif type_name == 'float':
            default = '0.0'  # or should it be NaN?
        elif type_name == 'string':
            default = 'kEmptyString'

        elif typ.resolved and isinstance(typ.resolved, ast.SimpleSum):
            sum_type = typ.resolved
            # Just make it the first variant.  We could define "Undef" for
            # each enum, but it doesn't seem worth it.
            default = '%s_e::%s' % (type_name, sum_type.types[0].name)

        else:
            default = 'nullptr'  # Sum or Product
        return default

    else:
        raise AssertionError()


def _HNodeExpr(typ, var_name):
    # type: (str, ast.TypeExpr, str) -> str
    none_guard = False

    if typ.IsOptional():
        typ = typ.children[0]  # descend one level

    if isinstance(typ, ast.ParameterizedType):
        code_str = '%s->PrettyTree()' % var_name
        none_guard = True

    elif isinstance(typ, ast.NamedType):

        type_name = typ.name

        if type_name in ('bool', 'int', 'uint16', 'BigInt', 'float', 'string'):
            code_str = "ToPretty(%s)" % var_name

        elif type_name == 'any':
            # This is used for _BuiltinFunc, _BuiltinProc.  There is not that much to customize here.
            code_str = 'Alloc<hnode::Leaf>(StrFromC("<extern>"), color_e::External)'  # % var_name

        elif type_name == 'id':  # was meta.UserType
            code_str = 'Alloc<hnode::Leaf>(Id_str(%s, false), color_e::UserType)' % var_name

        elif typ.resolved and isinstance(typ.resolved, ast.SimpleSum):
            # ASDL could generate ToPretty<T> ?
            code_str = 'Alloc<hnode::Leaf>(%s_str(%s), color_e::TypeName)' % (
                type_name, var_name)

        else:
            code_str = '%s->PrettyTree(do_abbrev, seen)' % var_name
            none_guard = True

    else:
        raise AssertionError()

    return code_str, none_guard


class ClassDefVisitor(visitor.AsdlVisitor):
    """Generate C++ declarations and type-safe enums."""

    def __init__(self, f, pretty_print_methods=True, debug_info=None):
        """
        Args:
          f: file to write to
          debug_info: dictionary fill in with info for GDB
        """
        visitor.AsdlVisitor.__init__(self, f)
        self.pretty_print_methods = pretty_print_methods
        self.debug_info = debug_info if debug_info is not None else {}

        self._shared_type_tags = {}
        self._product_counter = 64  # start halfway through the range 0-127

        self._products = []
        self._base_classes = defaultdict(list)

        self._subtypes = []

    def _EmitEnum(self, sum, sum_name, depth, strong=False, is_simple=False):
        enum = []
        int_to_type = {}
        add_suffix = not ('no_namespace_suffix' in sum.generate)
        for i, variant in enumerate(sum.types):
            if variant.shared_type:  # Copied from gen_python.py
                tag_num = self._shared_type_tags[variant.shared_type]
                # e.g. DoubleQuoted may have base types expr_t, word_part_t
                base_class = sum_name + '_t'
                bases = self._base_classes[variant.shared_type]
                if base_class in bases:
                    raise RuntimeError(
                        "Two tags in sum %r refer to product type %r" %
                        (sum_name, variant.shared_type))
                else:
                    bases.append(base_class)
                type_str = variant.shared_type
            else:
                tag_num = i + 1
                type_str = '%s__%s' % (sum_name, variant.name)
            int_to_type[tag_num] = type_str
            enum.append((variant.name, tag_num))  # zero is reserved

        if strong:
            enum_name = '%s_e' % sum_name if add_suffix else sum_name

            # Simple sum types can be STRONG since there's no possibility of multiple
            # inheritance!

            self.Emit('enum class %s {' % enum_name, depth)
            for name, tag_num in enum:
                self.Emit('%s = %d,' % (name, tag_num), depth + 1)
            self.Emit('};', depth)

            # type alias to match Python code
            self.Emit('typedef %s %s_t;' % (enum_name, sum_name), depth)
            self.Emit('', depth)

            if self.pretty_print_methods:
                self.Emit(
                    'BigStr* %s_str(%s tag, bool dot = true);' %
                    (sum_name, enum_name), depth)
                self.Emit('', depth)

        else:
            if is_simple:
                enum_name = '%s_i' % sum_name if add_suffix else sum_name
            else:
                enum_name = '%s_e' % sum_name if add_suffix else sum_name

            # Awkward struct/enum C++ idiom because:

            # 1. namespace can't be "imported" with 'using'
            # 2. plain enum pollutes outer namespace
            # 3. C++ 11 'enum class' does not allow conversion to int
            # 4. namespace and 'static const int' or 'static constexpr int' gives
            #    weird link errors
            # https://quuxplusone.github.io/blog/2020/09/19/value-or-pitfall/

            self.Emit('ASDL_NAMES %s {' % enum_name, depth)
            self.Emit('  enum no_name {', depth)
            for name, tag_num in enum:
                self.Emit('%s = %d,' % (name, tag_num), depth + 1)

            if is_simple:
                # Help in sizing array.  Note that we're 1-based.
                self.Emit('ARRAY_SIZE = %d,' % (len(enum) + 1), depth + 1)

            self.Emit('  };', depth)
            self.Emit('};', depth)

            self.Emit('', depth)

            if self.pretty_print_methods:
                self.Emit(
                    'BigStr* %s_str(int tag, bool dot = true);' % sum_name,
                    depth)
                self.Emit('', depth)

        return int_to_type

    def VisitSimpleSum(self, sum, name, depth):
        # Note: there can be more than 128 variants in a simple sum, because it's an
        # integer and doesn't have an object header.

        if 'integers' in sum.generate:
            self._EmitEnum(sum, name, depth, strong=False, is_simple=True)
            self.Emit('typedef int %s_t;' % name)
            self.Emit('')
        elif 'uint16' in sum.generate:
            self._EmitEnum(sum, name, depth, strong=False, is_simple=True)
            self.Emit('typedef uint16_t %s_t;' % name)
            self.Emit('')
        else:
            self._EmitEnum(sum, name, depth, strong=True)

    def VisitCompoundSum(self, sum, sum_name, depth):
        #log('%d variants in %s', len(sum.types), sum_name)

        # Must fit in 7 bit Obj::type_tag
        assert len(
            sum.types) < 64, 'sum type %r has too many variants' % sum_name

        # This is a sign that Python needs string interpolation!!!
        def Emit(s, depth=depth):
            self.Emit(s % sys._getframe(1).f_locals, depth)

        int_to_type = self._EmitEnum(sum, sum_name, depth)

        # Only add debug info for compound sums.
        self.debug_info['%s_t' % sum_name] = int_to_type

        # This is the base class.
        Emit('class %(sum_name)s_t {')
        # Can't be constructed directly.  Note: this shows up in uftrace in debug
        # mode, e.g. when we instantiate Token.  Do we need it?
        Emit(' protected:')
        Emit('  %s_t() {' % sum_name)
        Emit('  }')
        Emit(' public:')
        Emit('  int tag() const {')
        # There's no inheritance relationship, so we have to reinterpret_cast.
        Emit('    return ObjHeader::FromObject(this)->type_tag;')
        Emit('  }')

        if self.pretty_print_methods:
            self.Emit(
                '  hnode_t* PrettyTree(bool do_abbrev, Dict<int, bool>* seen = nullptr);'
            )

        Emit('  DISALLOW_COPY_AND_ASSIGN(%(sum_name)s_t)')
        Emit('};')
        Emit('')

        for variant in sum.types:
            if variant.shared_type:
                # Don't generate a class.
                pass
            else:
                super_name = '%s_t' % sum_name
                tag = 'static_cast<uint16_t>(%s_e::%s)' % (sum_name,
                                                           variant.name)
                class_name = '%s__%s' % (sum_name, variant.name)
                self._GenClass(variant.fields, class_name, [super_name], depth,
                               tag)

        # Generate 'extern' declarations for zero arg singleton globals
        for variant in sum.types:
            if not variant.shared_type and len(variant.fields) == 0:
                variant_name = variant.name
                Emit(
                    'extern GcGlobal<%(sum_name)s__%(variant_name)s> g%(sum_name)s__%(variant_name)s;'
                )

        # Allow expr::Const in addition to expr.Const.
        Emit('ASDL_NAMES %(sum_name)s {')
        for variant in sum.types:
            if variant.shared_type:
                continue

            # TODO: This produces a lint error, but IS USED via % reflection
            variant_name = variant.name

            if len(variant.fields) == 0:
                Emit(
                    '  static %(sum_name)s__%(variant_name)s* %(variant_name)s;'
                )
            else:
                Emit(
                    '  typedef %(sum_name)s__%(variant_name)s %(variant_name)s;'
                )
        Emit('};')
        Emit('')

    def _GenClassBegin(self, class_name, base_classes, depth):
        if base_classes:
            bases = ', '.join('public %s' % b for b in base_classes)
            self.Emit("class %s : %s {" % (class_name, bases), depth)
        else:
            self.Emit("class %s {" % class_name, depth)
        self.Emit(" public:", depth)

    def _GenClassEnd(self, class_name, depth):
        self.Emit('  DISALLOW_COPY_AND_ASSIGN(%s)' % class_name)
        self.Emit('};', depth)
        self.Emit('', depth)

    def _EmitMethodDecl(self, obj_header_str, depth):
        if self.pretty_print_methods:
            self.Emit(
                '  hnode_t* PrettyTree(bool do_abbrev, Dict<int, bool>* seen = nullptr);',
                depth)
            self.Emit('')

        self.Emit('  static constexpr ObjHeader obj_header() {')
        self.Emit('    return %s;' % obj_header_str)
        self.Emit('  }')
        self.Emit('')

    def _GenClassForList(self, class_name, base_classes, tag_num):
        depth = 0
        self._GenClassBegin(class_name, base_classes, depth)

        base_type_str = [b for b in base_classes if b.startswith('List<')][0]

        # Zero arg constructor
        self.Emit('  %s() : %s() {' % (class_name, base_type_str), depth)
        self.Emit('  }', depth)

        # One arg constructor used by Take.
        # This should be is PROTECTED, like the superclass, but Alloc<T> calls
        # it.  Hm.
        #self.Emit(' protected:')
        self.Emit(
            '  %s(%s* plain_list) : %s(plain_list) {' %
            (class_name, base_type_str, base_type_str), depth)
        self.Emit('  }', depth)

        self.Emit('  static %s* New() {' % class_name, depth)
        self.Emit('    return Alloc<%s>();' % class_name, depth)
        self.Emit('  }', depth)

        # Take() constructor
        self.Emit(
            '  static %s* Take(%s* plain_list) {' %
            (class_name, base_type_str), depth)
        self.Emit('    auto* result = Alloc<%s>(plain_list);' % class_name,
                  depth)
        self.Emit('    plain_list->SetTaken();', depth)
        self.Emit('    return result;', depth)
        self.Emit('  }', depth)

        # field_mask() should call List superclass, since say word_t won't have it
        obj_header_str = 'ObjHeader::TaggedSubtype(%d, field_mask())' % tag_num
        self._EmitMethodDecl(obj_header_str, depth)

        self._GenClassEnd(class_name, depth)

    def _GenClass(self,
                  fields,
                  class_name,
                  base_classes,
                  depth,
                  tag_num,
                  obj_header_str=''):
        """For Product and Constructor."""
        self._GenClassBegin(class_name, base_classes, depth)

        # Ensure that the member variables are ordered such that GC managed objects
        # come before any unmanaged ones because we use `HeapTag::Scanned`.
        managed_fields = []
        unmanaged_fields = []
        for f in fields:
            if _IsManagedType(f.typ):
                managed_fields.append(f)
            else:
                unmanaged_fields.append(f)
        all_fields = managed_fields + unmanaged_fields

        def FieldInitJoin(strs):
            # reflow doesn't work well here, so do it manually
            return ',\n        '.join(strs)

        # Ensure that the constructor params are listed in the same order as the
        # equivalent python constructors for compatibility in translated code.
        params = []
        for f in fields:
            params.append('%s %s' % (_GetCppType(f.typ), f.name))

        # Member initializers are in the same order as the member variables to
        # avoid compiler warnings (the order doesn't affect the semantics).
        inits = []
        for f in all_fields:
            inits.append('%s(%s)' % (f.name, f.name))

        # Define constructor with N args
        if len(inits):
            self.Emit('  %s(%s)' % (class_name, ', '.join(params)), depth)
            self.Emit('      : %s {' % FieldInitJoin(inits),
                      depth,
                      reflow=False)
            self.Emit('  }')
        else:
            self.Emit('  %s(%s) {}' % (class_name, ', '.join(params)), depth)
        self.Emit('')

        # Define static constructor with ZERO args.  Don't emit for types with no
        # fields.
        if fields:
            init_args = []
            for field in fields:
                init_args.append(_DefaultValue(field.typ))

            self.Emit(
                '  static %s* CreateNull(bool alloc_lists = false) { ' %
                class_name, depth)
            self.Emit(
                '    return Alloc<%s>(%s);' %
                (class_name, ', '.join(init_args)), depth)
            self.Emit('  }')
            self.Emit('')

        obj_header_str = 'ObjHeader::AsdlClass(%s, %d)' % (tag_num,
                                                           len(managed_fields))
        self._EmitMethodDecl(obj_header_str, depth)

        #
        # Members
        #
        for field in all_fields:
            self.Emit("  %s %s;" % (_GetCppType(field.typ), field.name))
        self.Emit('')

        self._GenClassEnd(class_name, depth)

    def VisitSubType(self, subtype):
        self._shared_type_tags[subtype.name] = self._product_counter

        # Also create these last. They may inherit from sum types that have yet
        # to be defined.
        self._subtypes.append((subtype, self._product_counter))
        self._product_counter += 1

    def VisitProduct(self, product, name, depth):
        self._shared_type_tags[name] = self._product_counter
        # Create a tuple of _GenClass args to create LAST.  They may inherit from
        # sum types that have yet to be defined.
        self._products.append((product, name, depth, self._product_counter))
        self._product_counter += 1

    def EmitFooter(self):
        # Now generate all the product types we deferred.
        for args in self._products:
            ast_node, name, depth, tag_num = args
            # Figure out base classes AFTERWARD.
            bases = self._base_classes[name]
            self._GenClass(ast_node.fields, name, bases, depth, tag_num)

        for args in self._subtypes:
            subtype, tag_num = args
            # Figure out base classes AFTERWARD.
            bases = self._base_classes[subtype.name]

            cpp_type = _GetCppType(subtype.base_class)
            assert cpp_type.endswith('*')  # hack
            cpp_type = cpp_type[:-1]
            bases.append(cpp_type)

            t = subtype.base_class.type_name
            if t == 'List':
                self._GenClassForList(subtype.name, bases, tag_num)

            elif t == 'Dict':
                raise AssertionError()
            else:
                #obj_header_str = ''
                raise AssertionError()


class MethodDefVisitor(visitor.AsdlVisitor):
    """Generate the body of pretty printing methods.

    We have to do this in another pass because types and schemas have
    circular dependencies.
    """

    def __init__(self, f, abbrev_ns=None, abbrev_mod_entries=None):
        visitor.AsdlVisitor.__init__(self, f)
        self.abbrev_ns = abbrev_ns
        self.abbrev_mod_entries = abbrev_mod_entries or []

    def _EmitList(self, list_str, item_type, out_val_name):
        # used in format strings
        c_item_type = _GetCppType(item_type)

        def _Emit(s):
            self.Emit(s % sys._getframe(1).f_locals, self.current_depth)

        _Emit(
            'hnode::Array* %(out_val_name)s = Alloc<hnode::Array>(Alloc<List<hnode_t*>>());'
        )
        _Emit(
            'for (ListIter<%(c_item_type)s> it(%(list_str)s); !it.Done(); it.Next()) {'
        )
        _Emit('  %(c_item_type)s v_ = it.Value();')

        child_code_str, none_guard = _HNodeExpr(item_type, 'v_')
        if none_guard:  # e.g. for List[Optional[value_t]]
            # TODO: could consolidate this logic with asdl/runtime.py NewLeaf(), which is prebuilt/
            child_code_str = (
                '(v_ == nullptr) ? Alloc<hnode::Leaf>(StrFromC("_"), color_e::OtherConst) : %s'
                % child_code_str)
        _Emit('  hnode_t* h = %(child_code_str)s;')
        _Emit('  %(out_val_name)s->children->append(h);')
        _Emit('}')

    def _EmitListPrettyPrint(self, field, out_val_name):
        typ = field.typ
        if typ.type_name == 'Optional':  # descend one level
            typ = typ.children[0]
        item_type = typ.children[0]

        self._EmitList('this->%s' % field.name, item_type, out_val_name)

    def _EmitDictPrettyPrint(self, field):
        typ = field.typ
        if typ.type_name == 'Optional':  # descend one level
            typ = typ.children[0]

        k_typ = typ.children[0]
        v_typ = typ.children[1]

        k_c_type = _GetCppType(k_typ)
        v_c_type = _GetCppType(v_typ)

        k_code_str, _ = _HNodeExpr(k_typ, 'k')
        v_code_str, _ = _HNodeExpr(v_typ, 'v')

        self.Emit('auto* unnamed = NewList<hnode_t*>();')
        self.Emit(
            'auto* hdict = Alloc<hnode::Record>(kEmptyString, StrFromC("{"), StrFromC("}"), NewList<Field*>(), unnamed);'
        )
        self.Emit(
            'for (DictIter<%s, %s> it(this->%s); !it.Done(); it.Next()) {' %
            (k_c_type, v_c_type, field.name))
        self.Emit('  auto k = it.Key();')
        self.Emit('  auto v = it.Value();')
        self.Emit('  unnamed->append(%s);' % k_code_str)
        self.Emit('  unnamed->append(%s);' % v_code_str)
        self.Emit('}')
        self.Emit('L->append(Alloc<Field>(StrFromC("%s"), hdict));' %
                  field.name)

    def _EmitCodeForField(self, field, counter):
        """Generate code that returns an hnode for a field."""
        out_val_name = 'x%d' % counter

        if field.typ.IsList():
            self.Emit('if (this->%s != nullptr) {  // List' % field.name)
            self.Indent()
            self._EmitListPrettyPrint(field, out_val_name)
            self.Emit('L->append(Alloc<Field>(StrFromC("%s"), %s));' %
                      (field.name, out_val_name))
            self.Dedent()
            self.Emit('}')

        elif field.typ.IsDict():
            self.Emit('if (this->%s != nullptr) {  // Dict' % field.name)
            self.Indent()
            self._EmitDictPrettyPrint(field)
            self.Dedent()
            self.Emit('}')

        elif field.typ.IsOptional():
            typ = field.typ.children[0]

            self.Emit('if (this->%s) {  // Optional' % field.name)
            child_code_str, _ = _HNodeExpr(typ, 'this->%s' % field.name)
            self.Emit('  hnode_t* %s = %s;' % (out_val_name, child_code_str))
            self.Emit('  L->append(Alloc<Field>(StrFromC("%s"), %s));' %
                      (field.name, out_val_name))
            self.Emit('}')

        else:
            var_name = 'this->%s' % field.name
            code_str, obj_none_guard = _HNodeExpr(field.typ, var_name)

            depth = self.current_depth
            if obj_none_guard:  # to satisfy MyPy type system
                pass
            self.Emit('hnode_t* %s = %s;' % (out_val_name, code_str), depth)

            self.Emit(
                'L->append(Alloc<Field>(StrFromC("%s"), %s));' %
                (field.name, out_val_name), depth)

    def _EmitPrettyPrintMethods(self,
                                class_name,
                                all_fields,
                                sum_name=None,
                                list_item_type=None):
        """
        """
        self.Emit('')
        self.Emit(
            'hnode_t* %s::PrettyTree(bool do_abbrev, Dict<int, bool>* seen) {'
            % class_name)

        # Similar to j8::HeapValueId()
        self.Emit('  seen = seen ? seen : Alloc<Dict<int, bool>>();')
        self.Emit('  int heap_id = ObjectId(this);')
        self.Emit('  if (dict_contains(seen, heap_id)) {')
        self.Emit('    return Alloc<hnode::AlreadySeen>(heap_id);')
        self.Emit('  }')
        self.Emit('  seen->set(heap_id, true);')
        self.Emit('')

        if list_item_type:
            self.Indent()
            self._EmitList('this', list_item_type, 'out_node')
            self.Dedent()
        else:
            if sum_name is not None:
                n = '%s_str(this->tag())' % sum_name
            else:
                n = 'StrFromC("%s")' % class_name

            abbrev_name = '_%s' % class_name

            if abbrev_name in self.abbrev_mod_entries:
                self.Emit('  if (do_abbrev) {')
                self.Emit('    auto* p = %s::%s(this);' %
                          (self.abbrev_ns, abbrev_name))
                self.Emit('    if (p) {')
                self.Emit('      return p;')
                self.Emit('    }')
                self.Emit('  }')
            else:
                #self.Emit('  // no abbrev %s' % abbrev_name)
                pass

            self.Emit('  hnode::Record* out_node = runtime::NewRecord(%s);' %
                      n)
            if all_fields:
                self.Emit('  List<Field*>* L = out_node->fields;')
                self.Emit('')

            # Use the runtime type to be more like asdl/format.py
            for local_id, field in enumerate(all_fields):
                #log('%s :: %s', field_name, field_desc)
                self.Indent()
                self._EmitCodeForField(field, local_id)
                self.Dedent()
                self.Emit('')
        self.Emit('  return out_node;')
        self.Emit('}')
        self.Emit('')

    def _EmitStrFunction(self,
                         sum,
                         sum_name,
                         depth,
                         strong=False,
                         simple=False):
        add_suffix = not ('no_namespace_suffix' in sum.generate)
        if add_suffix:
            if simple:
                enum_name = '%s_i' % sum_name
            else:
                enum_name = '%s_e' % sum_name
        else:
            enum_name = sum_name

        if strong:
            self.Emit(
                'BigStr* %s_str(%s tag, bool dot) {' % (sum_name, enum_name),
                depth)
        else:
            self.Emit('BigStr* %s_str(int tag, bool dot) {' % sum_name, depth)

        buf_size = 32
        v_max = max(len(variant.name) for variant in sum.types)
        s_max = v_max + 1 + len(sum_name) + 1  # for . and NUL
        if s_max > buf_size:
            raise RuntimeError('Sum name %r + variant name is too long' %
                               sum_name)

        self.Emit('  char buf[%d];' % buf_size, depth)
        self.Emit('  const char* v = nullptr;', depth)
        self.Emit('  switch (tag) {', depth)
        for variant in sum.types:
            self.Emit('case %s::%s:' % (enum_name, variant.name), depth + 1)
            self.Emit('  v = "%s"; break;' % variant.name, depth + 1)

        self.Emit('default:', depth + 1)
        self.Emit('  assert(0);', depth + 1)

        self.Emit('  }', depth)
        self.Emit('  if (dot) {', depth)
        self.Emit('    snprintf(buf, %d, "%s.%%s", v);' % (buf_size, sum_name),
                  depth)
        self.Emit('    return StrFromC(buf);', depth)
        self.Emit('  } else {', depth)
        self.Emit('    return StrFromC(v);', depth)
        self.Emit('  }', depth)
        self.Emit('}', depth)

    def VisitSimpleSum(self, sum, name, depth):
        if 'integers' in sum.generate or 'uint16' in sum.generate:
            self._EmitStrFunction(sum, name, depth, strong=False, simple=True)
        else:
            self._EmitStrFunction(sum, name, depth, strong=True)

    def VisitCompoundSum(self, sum, sum_name, depth):
        self._EmitStrFunction(sum, sum_name, depth)

        # Generate definitions for the for zero arg singleton globals
        for variant in sum.types:
            if variant.shared_type:
                continue
            if len(variant.fields) == 0:
                variant_name = variant.name
                self.Emit('')
                self.Emit('%s__%s* %s::%s = &g%s__%s.obj;' %
                          (sum_name, variant_name, sum_name, variant_name,
                           sum_name, variant_name))
                self.Emit('')
                self.Emit('GcGlobal<%s__%s> g%s__%s = ' %
                          (sum_name, variant_name, sum_name, variant_name))
                self.Emit('  { ObjHeader::Global(%s_e::%s) };' %
                          (sum_name, variant_name))

        for variant in sum.types:
            if variant.shared_type:
                continue
            all_fields = variant.fields
            class_name = '%s__%s' % (sum_name, variant.name)
            self._EmitPrettyPrintMethods(class_name,
                                         all_fields,
                                         sum_name=sum_name)

        # Emit dispatch WITHOUT using 'virtual'
        self.Emit('')
        self.Emit(
            'hnode_t* %s_t::PrettyTree(bool do_abbrev, Dict<int, bool>* seen) {'
            % sum_name)
        self.Emit('  switch (this->tag()) {', depth)

        for variant in sum.types:
            if variant.shared_type:
                subtype_name = variant.shared_type
            else:
                subtype_name = '%s__%s' % (sum_name, variant.name)

            self.Emit('  case %s_e::%s: {' % (sum_name, variant.name), depth)
            self.Emit(
                '    %s* obj = static_cast<%s*>(this);' %
                (subtype_name, subtype_name), depth)
            self.Emit('    return obj->PrettyTree(do_abbrev, seen);', depth)
            self.Emit('  }', depth)

        self.Emit('  default:', depth)
        self.Emit('    assert(0);', depth)

        self.Emit('  }')
        self.Emit('}')

    def VisitProduct(self, product, name, depth):
        self._EmitPrettyPrintMethods(name, product.fields)

    def VisitSubType(self, subtype):
        list_item_type = None
        b = subtype.base_class
        if isinstance(b, ast.ParameterizedType):
            if b.type_name == 'List':
                list_item_type = b.children[0]
        self._EmitPrettyPrintMethods(subtype.name, [],
                                     list_item_type=list_item_type)

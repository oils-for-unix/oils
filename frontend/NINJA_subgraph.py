"""
frontend/NINJA_subgraph.py
"""

from __future__ import print_function

from build import ninja_lib
from build.ninja_lib import log

_ = log


def NinjaGraph(ru):
    n = ru.n

    ru.comment('Generated by %s' % __name__)

    n.rule('consts-gen',
           command='_bin/shwrap/consts_gen $action $out_prefix',
           description='consts_gen $action $out_prefix')

    n.rule('flag-gen',
           command='_bin/shwrap/flag_gen $action $out_prefix',
           description='flag_gen $action $out_prefix')

    n.rule('option-gen',
           command='_bin/shwrap/option_gen $action $out_prefix',
           description='consts_gen $action $out_prefix')

    n.rule('signal-gen',
           command='_bin/shwrap/signal_gen $action $out_prefix',
           description='signal_gen $action $out_prefix')

    ru.py_binary('frontend/consts_gen.py')

    ru.py_binary('frontend/flag_gen.py')

    # TODO: hook this up
    #ru.py_binary('frontend/lexer_gen.py')

    ru.py_binary('frontend/option_gen.py')

    ru.py_binary('frontend/signal_gen.py')

    prefix = '_gen/frontend/id_kind.asdl'
    n.build([prefix + '.h', prefix + '.cc'],
            'consts-gen', [],
            implicit=['_bin/shwrap/consts_gen'],
            variables=[
                ('out_prefix', prefix),
                ('action', 'cpp'),
            ])
    n.newline()

    ru.cc_library(
        '//frontend/help_meta',
        srcs=['_gen/frontend/help_meta.cc'],
        # generated by build/py.all -> build/doc.sh all-help -> doctools/help_gen.py
        generated_headers=['_gen/frontend/help_meta.h'])

    ru.cc_library('//frontend/id_kind.asdl',
                  srcs=['_gen/frontend/id_kind.asdl.cc'],
                  generated_headers=['_gen/frontend/id_kind.asdl.h'])

    # Similar to above
    prefix = '_gen/frontend/consts'
    n.build([prefix + '.h', prefix + '.cc'],
            'consts-gen', [],
            implicit=['_bin/shwrap/consts_gen'],
            variables=[
                ('out_prefix', prefix),
                ('action', 'cpp-consts'),
            ])
    n.newline()

    ru.cc_library(
        '//frontend/consts',
        srcs=['_gen/frontend/consts.cc'],
        generated_headers=['_gen/frontend/consts.h'],
        # See header
        deps=[
            '//core/runtime.asdl',
            '//frontend/id_kind.asdl',
            '//frontend/option.asdl',
            '//frontend/types.asdl',
        ])

    prefix = '_gen/frontend/arg_types'
    n.build([prefix + '.h', prefix + '.cc'],
            'flag-gen', [],
            implicit=['_bin/shwrap/flag_gen'],
            variables=[
                ('out_prefix', prefix),
                ('action', 'cpp'),
            ])
    n.newline()

    ru.cc_library(
        '//frontend/arg_types',
        generated_headers=['_gen/frontend/arg_types.h'],
        srcs=['_gen/frontend/arg_types.cc'],
        deps=['//cpp/frontend_flag_spec'],
    )

    ru.cc_binary(
        'frontend/arg_types_test.cc',
        deps=['//frontend/arg_types', '//mycpp/runtime'],
        matrix=ninja_lib.COMPILERS_VARIANTS,
    )

    prefix = '_gen/frontend/option.asdl'
    # no .cc file
    n.build([prefix + '.h'],
            'option-gen', [],
            implicit=['_bin/shwrap/option_gen'],
            variables=[
                ('out_prefix', prefix),
                ('action', 'cpp'),
            ])
    n.newline()

    ru.cc_library('//frontend/option.asdl',
                  srcs=[],
                  generated_headers=['_gen/frontend/option.asdl.h'])

    prefix = '_gen/frontend/signal'
    n.build([prefix + '.h', prefix + '.cc'],
            'signal-gen', [],
            implicit=['_bin/shwrap/signal_gen'],
            variables=[
                ('out_prefix', prefix),
                ('action', 'cpp'),
            ])
    n.newline()

    ru.cc_library('//frontend/signal',
                  srcs=['_gen/frontend/signal.cc'],
                  generated_headers=['_gen/frontend/signal.h'])

    ru.asdl_library('frontend/types.asdl', pretty_print_methods=False)

    # Uses core/value.asdl, but value.asdl also depeneds on frontend/syntax.asdl
    #
    # In Python, that an import line:
    # if TYPE_CHECKING:
    #    from _devbuild.gen.value_asdl import value_t
    #
    # In C++, it creates a forward declaration in the header namespace value_asdl { class value_t }
    # But an #include in the .cc file, I guess for pretty printing?  Yes
    #
    # Questions:
    # - Do we need the deps at all?  We have different deps
    #   - #include "hnode.asdl.h" - if pretty_print_methods
    #   - #include "id_kind_asdl.h" - if app_types - TODO: should refactor this
    #     - this is using by VALUE, not just by POINTER
    # - Should we create a single asdl_library() target?
    # - What will we do when we switch to tagged pointers?  Then we can't
    # forward declare?

    ru.asdl_library(
        'frontend/syntax.asdl',
        deps=[
            # #include in header file
            # Problem: asdl_main.py hard-codes this dependency
            '//frontend/id_kind.asdl',

            # This is a circular dep.
            # Hm it did not create a problem?  I guess only cc_library() deps
            # can't be circular?
            '//core/value.asdl',
        ],
        abbrev_module='frontend.syntax_abbrev',
    )

    ru.cc_binary('frontend/syntax_asdl_test.cc',
                 deps=['//frontend/syntax.asdl'],
                 matrix=ninja_lib.COMPILERS_VARIANTS)

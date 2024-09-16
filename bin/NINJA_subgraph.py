"""
bin/NINJA_subgraph.py
"""
from __future__ import print_function

from glob import glob
from fnmatch import fnmatch

from build import ninja_lib
from build.ninja_lib import log

_ = log

# TODO: should have dependencies with sh_binary
RULES_PY = 'build/ninja-rules-py.sh'


def NinjaGraph(ru):
    n = ru.n

    ru.comment('Generated by %s' % __name__)

    #
    # Files embedded in binary
    #

    n.rule('embedded-file-gen',
           command='_bin/shwrap/embedded_file_gen $in > $out',
           description='embedded_file_gen $in $out')

    # Generated by build/py.sh all -> build/doc.sh all-help
    # I wish Ninja had DIRECTORY-level dependencies?  Because this should
    # ultimately depend on doc/ref/*.md
    # We could probably create a _build/ninja-stamp/HELP file and so forth
    files = glob('_devbuild/help/*')

    # OSH and YSH stdlib
    tmp = glob('stdlib/ysh/*.ysh') + glob('stdlib/osh/*.sh')

    # Remove this?
    tmp.extend(glob('stdlib/*.ysh'))

    # exclude test files
    for path in tmp:
        if fnmatch(path, '*-test.ysh'):
            continue
        if fnmatch(path, '*-test.sh'):
            continue
        if fnmatch(path, '*/draft-*'):
            continue

        files.append(path)

    # Make sure it's DETERMINISTIC
    files.sort()

    n.build(['_gen/bin/text_files.cc'],
            'embedded-file-gen',
            files,
            implicit=['_bin/shwrap/embedded_file_gen'])
    n.newline()

    ru.cc_library('//bin/text_files', srcs=['_gen/bin/text_files.cc'])

    #
    # Main Programs
    #

    for main_name in ('osh_eval', 'oils_for_unix'):
        for translator in ('mycpp', 'mycpp-souffle'):
            with open('_build/NINJA/bin.%s/translate.txt' % main_name) as f:
                deps = [line.strip() for line in f]

            prefix = '_gen/bin/%s.%s' % (main_name, translator)
            outputs = [prefix + '.cc', prefix + '.h']

            variables = [
                ('out_prefix', prefix),
                ('main_name', main_name),
                ('translator', translator),
                ('preamble', 'cpp/preamble.h'),
            ]
            if translator == 'mycpp-souffle':
                variables.append(('extra_mycpp_opts', '--minimize-stack-roots'))

            n.build(outputs,
                    'gen-oils-for-unix',
                    deps,
                    implicit=['_bin/shwrap/mycpp_main', RULES_PY],
                    variables=variables)

            if main_name == 'oils_for_unix':
                # The main program!
                if translator == 'mycpp-souffle':
                    bin_path = '%s/oils-for-unix' % translator
                else:
                    # Keep the default mycpp build at the original location to
                    # avoid breaking benchmarks and tests.
                    bin_path = 'oils-for-unix'
                symlinks = ['osh', 'ysh']
            else:
                symlinks = []
                bin_path = None  # use default

            ru.cc_binary(
                '_gen/bin/%s.%s.cc' % (main_name, translator),
                bin_path=bin_path,
                symlinks=symlinks,
                preprocessed=True,
                matrix=(ninja_lib.COMPILERS_VARIANTS + ninja_lib.GC_PERF_VARIANTS +
                        ninja_lib.OTHER_VARIANTS),
                deps=[
                    '//bin/text_files',
                    '//cpp/core',
                    '//cpp/data_lang',
                    '//cpp/fanos',
                    '//cpp/libc',
                    '//cpp/osh',
                    '//cpp/pgen2',
                    '//cpp/pylib',
                    '//cpp/stdlib',
                    '//cpp/frontend_flag_spec',
                    '//cpp/frontend_match',
                    '//cpp/frontend_pyreadline',
                    '//data_lang/nil8.asdl',
                    '//display/pretty.asdl',
                    '//frontend/arg_types',
                    '//frontend/consts',
                    '//frontend/help_meta',
                    '//frontend/id_kind.asdl',
                    '//frontend/option.asdl',
                    '//frontend/signal',
                    '//frontend/syntax.asdl',
                    '//frontend/types.asdl',
                    '//core/optview',
                    '//core/runtime.asdl',
                    '//core/value.asdl',
                    '//osh/arith_parse',
                    '//ysh/grammar',
                    '//mycpp/runtime',
                ])

#!/usr/bin/env python2
"""
build/ninja_main.py - invoked by ./NINJA-config.sh

See build/README.md for the code and data layout.
"""
from __future__ import print_function

import cStringIO
from glob import glob
import os
import re
import sys

from build import ninja_lib
from build.ninja_lib import log

from asdl import NINJA_subgraph as asdl_subgraph
from bin import NINJA_subgraph as bin_subgraph
from core import NINJA_subgraph as core_subgraph
from cpp import NINJA_subgraph as cpp_subgraph
from data_lang import NINJA_subgraph as data_lang_subgraph
from display import NINJA_subgraph as display_subgraph
from frontend import NINJA_subgraph as frontend_subgraph
from osh import NINJA_subgraph as osh_subgraph
from mycpp import NINJA_subgraph as mycpp_subgraph
from pea import NINJA_subgraph as pea_subgraph
from prebuilt import NINJA_subgraph as prebuilt_subgraph
from yaks import NINJA_subgraph as yaks_subgraph
from ysh import NINJA_subgraph as ysh_subgraph

from vendor import ninja_syntax

# The file Ninja runs by default.
BUILD_NINJA = 'build.ninja'


def TarballManifest(some_files):
    names = []

    # Code we know about
    names.extend(some_files)

    names.extend([
        # Text
        'LICENSE.txt',
        'README-native.txt',
        'INSTALL.txt',
        'configure',
        'install',
        'doc/osh.1',

        # Build Scripts
        'build/common.sh',
        'build/native.sh',
        'build/static-oils.sh',

        # These 2 are used by build/ninja-rules-cpp.sh
        'build/py2.sh',
        'build/dev-shell.sh',
        'build/ninja-rules-cpp.sh',

        # These are in build/py.sh, not Ninja.  Should probably put them in Ninja.
        #'_gen/frontend/help_meta.h',
        '_gen/frontend/match.re2c.h',
        '_gen/frontend/id_kind.asdl_c.h',
        '_gen/frontend/types.asdl_c.h',
    ])

    # For configure
    names.extend(glob('build/detect-*.c'))

    names.extend(glob('cpp/*.h'))
    names.extend(glob('mycpp/*.h'))
    names.extend(glob('asdl/*.h'))

    # ONLY the headers
    names.extend(glob('prebuilt/*/*.h'))

    names.sort()  # Pass them to tar sorted

    # Check for dupes here
    unique = sorted(set(names))
    if names != unique:
        dupes = [n for n in names if names.count(n) > 1]
        raise AssertionError("Tarball manifest shouldn't have duplicates: %s" %
                             dupes)

    for name in names:
        print(name)


def _WinPath(s):
    return s.replace('/', '\\')


def BatchFunctions(app_name, cc_sources, f, argv0):
    objects = []
    in_out = []
    for src in sorted(cc_sources):
        # e.g. _build/obj/cxx-dbg-sh/posix.o
        prefix, _ = os.path.splitext(src)

        #obj = '_build/obj/$compiler-$variant-sh/%s.o' % prefix
        obj = '_build/obj/cxx-dbg/%s.o' % prefix
        in_out.append((src, obj))

    obj_dirs = sorted(set(os.path.dirname(obj) for _, obj in in_out))
    for d in obj_dirs:
        print('mkdir %s' % _WinPath(d), file=f)

    print('', file=f)

    for i, (src, obj) in enumerate(in_out):
        #obj_quoted = '"%s"' % obj
        objects.append(_WinPath(obj))

        # TODO: OILS_WIN32 is a hack, should have ./configure for dprintf()
        print('g++ -I . -D OILS_WIN32 -D MARK_SWEEP -c -o %s %s' %
              (_WinPath(obj), _WinPath(src)),
              file=f)
        print('if %ERRORLEVEL% neq 0 goto :error', file=f)

    print('', file=f)

    # Link

    out_dir = '_bin/cxx-dbg'
    out = '%s/%s' % (out_dir, app_name)
    print('mkdir %s' % _WinPath(out_dir), file=f)
    print('g++ -o %s %s' % (_WinPath(out), ' '.join(objects)), file=f)

    print('', file=f)
    print(':error', file=f)
    print('   echo ERROR %ERRORLEVEL%', file=f)
    print('   exit /b %ERRORLEVEL%', file=f)


def ShellFunctions(app_name, cc_sources, f, argv0):
    """
    Generate a shell fragment that invokes the same function that build.ninja
    does
    """
    # oils_for_unix -> oils-for-unix
    app_name_hyphens = app_name.replace('_', '-')

    print('''\
main() {
  ### Compile oils-for-unix into _bin/$compiler-$variant-sh/ (not with ninja)

  parse_flags "$@"

  # Copy into locals
  local compiler=$FLAG_cxx
  local variant=$FLAG_variant
  local translator=$FLAG_translator
  local skip_rebuild=$FLAG_skip_rebuild

  local out_name=%s

  local out_dir
  case $translator in
    mycpp)
      out_dir=_bin/$compiler-$variant-sh
      ;;
    *)
      out_dir=_bin/$compiler-$variant-sh/$translator
      ;;
  esac
  local out_path=$out_dir/$out_name$FLAG_suffix

  echo
  echo "$0: Building $out_name: $out_path"
  echo "    PWD = $PWD"
  echo "    cxx = $compiler"
  echo "    variant = $variant"
  echo "    translator = $translator"
  echo "    suffix = $FLAG_suffix"
  if test -n "$FLAG_without_readline"; then
    echo "    without_readline = $FLAG_without_readline"
  fi
  if test -n "$skip_rebuild"; then
    echo "    skip_rebuild = $skip_rebuild"
  fi

  if test -n "$skip_rebuild" && test -f "$out_path"; then
    echo
    echo "$0: SKIPPING build because $out_path exists"
    echo
    return
  fi

  echo
''' % app_name_hyphens,
          file=f)

    objects = []

    # Filenames that depend on the translator
    in_out = [
        ('_gen/bin/%s.$translator.cc' % app_name,
         '_build/obj/$compiler-$variant-sh/_gen/bin/%s.$translator.o' %
         app_name),
        ('_gen/bin/%s.$translator-main.cc' % app_name,
         '_build/obj/$compiler-$variant-sh/_gen/bin/%s.$translator-main.o' %
         app_name),
    ]
    for src in sorted(cc_sources):
        # e.g. _build/obj/cxx-dbg-sh/posix.o
        prefix, _ = os.path.splitext(src)

        # HACK to skip the special ones above
        if re.match(r'.*\.mycpp.*\.cc$', src):
            continue

        obj = '_build/obj/$compiler-$variant-sh/%s.o' % prefix
        in_out.append((src, obj))

    if 0:
        from pprint import pformat
        log('cc_sources = %s', pformat(cc_sources))
        log('in_out = %s', pformat(in_out))

    bin_dir = '_bin/$compiler-$variant-sh/$translator'
    obj_dirs = sorted(set(os.path.dirname(obj) for _, obj in in_out))

    all_dirs = [bin_dir] + obj_dirs
    # Double quote
    all_dirs = ['"%s"' % d for d in all_dirs]

    print('  mkdir -p \\', file=f)
    print('    %s' % ' \\\n    '.join(all_dirs), file=f)
    print('', file=f)

    do_fork = ''

    for i, (src, obj) in enumerate(in_out):
        obj_quoted = '"%s"' % obj
        objects.append(obj_quoted)

        # Only fork one translation unit that we know to be slow
        if src.endswith('.$translator.cc'):
            # There should only be one forked translation unit
            # It can be turned off with OILS_PARALLEL_BUILD= _build/oils
            assert do_fork == ''
            do_fork = '_do_fork=$OILS_PARALLEL_BUILD'
        else:
            do_fork = ''

        if do_fork:
            print('  # Potentially fork this translation unit with &', file=f)
            print('  %s \\' % do_fork, file=f)
        indent = '  ' if do_fork else ''
        print('  %s_compile_one "$compiler" "$variant" "" \\' % indent, file=f)
        print('    %s %s' % (src, obj_quoted), file=f)
        if do_fork:
            print(
                '  _do_fork=  # work around bug in some versions of the dash shell',
                file=f)
        print('', file=f)

    print('  # wait for the translation unit before linking', file=f)
    print('  echo WAIT', file=f)
    # time -p shows any excess parallelism on 2 cores
    # example: oils_for_unix.mycpp.cc takes ~8 seconds longer to compile than all
    # other translation units combined!

    # Timing isn't POSIX
    #print('  time -p wait', file=f)
    print('  wait', file=f)
    print('', file=f)

    print('  echo "LINK $out_path"', file=f)
    # put each object on its own line, and indent by 4
    # note: can't have spaces in filenames
    print('  set -- \\', file=f)
    print('    %s' % (' \\\n    '.join(objects)), file=f)
    print('', file=f)

    # Strip opt binary
    # TODO: provide a way for the user to get symbols?

    print('''\

  link "$compiler" "$variant" "" "$out_path" "$@"

  if test "$variant" = opt; then
    strip -o "$out_path.stripped" "$out_path"
  fi

  # Symlink to unstripped binary for benchmarking
  cd "$out_dir"  # dir may have spaces
  for symlink in "osh$FLAG_suffix" "ysh$FLAG_suffix"; do
    # like ln -v, which we can't use portably
    echo "    $symlink -> $out_name$FLAG_suffix"
    ln -s -f "$out_name$FLAG_suffix" $symlink
  done
}

main "$@"
''',
          file=f)


def WritePreprocessed(n, cc_sources):
    # See how much input we're feeding to the compiler.  Test C++ template
    # explosion, e.g. <unordered_map>
    #
    # Limit to {dbg,opt} so we don't generate useless rules.  Invoked by
    # metrics/source-code.sh

    pre_matrix = [
        ('cxx', 'dbg'),
        ('cxx', 'opt'),
        ('clang', 'dbg'),
        ('clang', 'opt'),
    ]
    for compiler, variant in pre_matrix:
        preprocessed = []
        for src in cc_sources:
            # e.g. mycpp/gc_heap.cc -> _build/preprocessed/cxx-dbg/mycpp/gc_heap.cc
            pre = '_build/preprocessed/%s-%s/%s' % (compiler, variant, src)
            preprocessed.append(pre)

        # Summary file
        n.build('_build/preprocessed/%s-%s.txt' % (compiler, variant),
                'line_count', preprocessed)
        n.newline()


def InitSteps(n):
    """Wrappers for build/ninja-rules-*.sh

    Some of these are defined in mycpp/NINJA_subgraph.py.  Could move them here.
    """
    #
    # Compiling and linking
    #

    # Preprocess one translation unit
    n.rule(
        'preprocess',
        # compile_one detects the _build/preprocessed path
        command=
        'build/ninja-rules-cpp.sh compile_one $compiler $variant $more_cxx_flags $in $out',
        description='PP $compiler $variant $more_cxx_flags $in $out')
    n.newline()

    n.rule('line_count',
           command='build/ninja-rules-cpp.sh line_count $out $in',
           description='line_count $out $in')
    n.newline()

    # Compile one translation unit
    n.rule(
        'compile_one',
        command=
        'build/ninja-rules-cpp.sh compile_one $compiler $variant $more_cxx_flags $in $out $out.d',
        depfile='$out.d',
        # no prefix since the compiler is the first arg
        description='$compiler $variant $more_cxx_flags $in $out')
    n.newline()

    # Link objects together
    n.rule(
        'link',
        command=
        'build/ninja-rules-cpp.sh link $compiler $variant $more_link_flags $out $in',
        description='LINK $compiler $variant $more_link_flags $out $in')
    n.newline()

    # 1 input and 2 outputs
    n.rule('strip',
           command='build/ninja-rules-cpp.sh strip_ $in $out',
           description='STRIP $in $out')
    n.newline()

    # cc_binary can have symliks
    n.rule('symlink',
           command='build/ninja-rules-cpp.sh symlink $out $symlink_val',
           description='SYMLINK $out $symlink_val')
    n.newline()

    #
    # Code generators
    #

    n.rule(
        'write-shwrap',
        # $in must start with main program
        command='build/ninja-rules-py.sh write-shwrap $template $out $in',
        description='make-shwrap $template $out $in')
    n.newline()

    n.rule('write-main',
           command=
           'build/ninja-rules-py.sh write-main $template $out $main_namespace',
           description='write-main $out $main_namespace')
    n.newline()

    # Trivial build rule, for bin/mycpp_main -> _bin/shwrap/mycpp_souffle
    # while adding implicit deps
    n.rule('cp', command='cp $in $out', description='cp $in $out')
    n.newline()


def main(argv):
    try:
        action = argv[1]
    except IndexError:
        action = 'ninja'

    try:
        app_name = argv[2]
    except IndexError:
        app_name = 'oils_for_unix'

    if action == 'ninja':
        f = open(BUILD_NINJA, 'w')
    else:
        f = cStringIO.StringIO()  # thrown away

    n = ninja_syntax.Writer(f)
    ru = ninja_lib.Rules(n)

    ru.comment('InitSteps()')
    InitSteps(n)

    #
    # Create the graph.
    #

    asdl_subgraph.NinjaGraph(ru)
    ru.comment('')

    # translate-mycpp rule
    mycpp_subgraph.NinjaGraph(ru)
    ru.comment('')

    bin_subgraph.NinjaGraph(ru)
    ru.comment('')

    core_subgraph.NinjaGraph(ru)
    ru.comment('')

    cpp_subgraph.NinjaGraph(ru)
    ru.comment('')

    data_lang_subgraph.NinjaGraph(ru)
    ru.comment('')

    display_subgraph.NinjaGraph(ru)
    ru.comment('')

    frontend_subgraph.NinjaGraph(ru)
    ru.comment('')

    ysh_subgraph.NinjaGraph(ru)
    ru.comment('')

    osh_subgraph.NinjaGraph(ru)
    ru.comment('')

    pea_subgraph.NinjaGraph(ru)
    ru.comment('')

    prebuilt_subgraph.NinjaGraph(ru)
    ru.comment('')

    yaks_subgraph.NinjaGraph(ru)
    ru.comment('')

    deps = ninja_lib.Deps(ru)
    # Materialize all the cc_binary() rules
    deps.WriteRules()

    main_cc = '_gen/bin/%s.mycpp-main.cc' % app_name

    # Collect sources for metrics, tarball, shell script
    cc_sources = deps.SourcesForBinary(main_cc)

    if 0:
        from pprint import pprint
        pprint(cc_sources)

    # TODO: could thin these out, not generate for unit tests, etc.
    WritePreprocessed(n, cc_sources)

    ru.WritePhony()

    n.default(['_bin/cxx-asan/osh', '_bin/cxx-asan/ysh'])

    if action == 'ninja':
        log('  (%s) -> %s (%d targets)', argv[0], BUILD_NINJA,
            n.num_build_targets())

    elif action == 'shell':
        ShellFunctions(app_name, cc_sources, sys.stdout, argv[0])

    elif action == 'batch':
        # TODO: write batch file
        BatchFunctions(app_name, cc_sources, sys.stdout, argv[0])

    elif action == 'tarball-manifest':
        names = list(cc_sources)  # copy

        h = deps.HeadersForBinary(main_cc)
        names.extend(h)

        if app_name == 'oils_for_unix':
            # TODO: SourcesForBinary() and HeadersForBinary can take MULTIPLE
            # -main.cc
            names.extend([
                '_gen/bin/%s.mycpp-nosouffle.cc' % app_name,
                '_gen/bin/%s.mycpp-nosouffle-main.cc' % app_name,
            ])
            names.append('_build/oils.sh')
        else:
            names.append('_build/%s.sh' % app_name)
            names.append('_build/%s.bat' % app_name)

        TarballManifest(names)

    elif action == 'app-deps':
        for name in cc_sources:
            print(name)
        print('---')
        h_sources = deps.HeadersForBinary(main_cc)
        for name in h_sources:
            print(name)

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)

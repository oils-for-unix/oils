#!/bin/bash
#
# Usage:
#   ./mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR

readonly REPO_ROOT=~/git/oilshell/oil

readonly MYPY_REPO=~/git/languages/mypy

# for 'perf'.  Technically this may slow things down, but it was in the noise
# on parsing configure-coreutils.
CPPFLAGS="$CXXFLAGS -fno-omit-frame-pointer"

# User can set CXX=, like they can set CC= for oil.ovm
# The ovm-build benchmark explicitly sets this to GCC or Clang.
if test -z "${CXX:-}"; then
  if test -f $CLANGXX; then
    # note: Clang doesn't inline MatchOshToken!
    CXX=$CLANGXX

    # Show more errors -- this flag is Clang-only.
    CPPFLAGS="$CPPFLAGS -ferror-limit=1000"
  else
    # equivalent of 'cc' for C++ langauge
    # https://stackoverflow.com/questions/172587/what-is-the-difference-between-g-and-gcc
    CXX='c++'
  fi
fi

# Always build with Address Sanitizer
readonly DBG_FLAGS="$CPPFLAGS -O0 -g"

export ASAN_SYMBOLIZER_PATH=$CLANG_DIR_RELATIVE/bin/llvm-symbolizer
# https://github.com/google/sanitizers/wiki/AddressSanitizerLeakSanitizer
export ASAN_OPTIONS='detect_leaks=0'

asdl-demo() {
  build/dev.sh oil-asdl-to-cpp
  $CXX -o _bin/oil_mycpp $DBG_FLAGS \
    -I _build/cpp \
    -I _devbuild/gen \
    -I mycpp \
    bin/oil.cc mycpp/mylib.cc -lstdc++

  echo '___'

  _bin/oil_mycpp
}

mycpp() {
  ### Run mycpp (in a virtualenv because it depends on Python 3 / MyPy)

  local out=$1
  shift

  # created by mycpp/run.sh
  ( source mycpp/_tmp/mycpp-venv/bin/activate
    time PYTHONPATH=$MYPY_REPO MYPYPATH=$REPO_ROOT:$REPO_ROOT/native \
      mycpp/mycpp_main.py "$@" > $out
  )
}

example-skeleton() {
  local namespace=$1
  shift

  cat <<EOF
#include "mylib.h"

EOF

  cat "$@"

  # TODO: This should find main(List<str>* argv) in the namespace
  cat <<EOF

int main(int argc, char **argv) {
  $namespace::run_tests();
}
EOF

}

cpp-skeleton() {
  local namespace=$1
  shift

  cat <<EOF
#include "dumb_alloc.h"
#include "mylib.h"
#include "preamble.h"  // hard-coded stuff

EOF

  cat "$@"

  cat <<EOF
int main(int argc, char **argv) {
  //log("%p", arith_parse::kNullLookup[1].nud);
  auto* args = new List<Str*>();
  for (int i = 0; i < argc; ++i) {
    args->append(new Str(argv[i]));
  }
  int status;

  // For benchmarking
  char* repeat = getenv("REPEAT");
  if (repeat) {
    Str* r = new Str(repeat);
    int n = to_int(r);
    log("Running %d times", n);
    for (int i = 0; i < n; ++i) { 
      status = $namespace::main(args);
    }
    // TODO: clear memory?
  } else {
    status = $namespace::main(args);
  }

  dumb_alloc::Summarize();
  return status;
}

// hard-coded definitions!
#include "postamble.cc"
EOF

}

compile() {
  local out=$1
  shift

  local flags="$CPPFLAGS"
  local link_flags=''
  case $out in
    *.opt)
      flags="$CPPFLAGS -O2 -g -D DUMB_ALLOC"
      ;;
    *.uftrace)
      # -O0 creates a A LOT more data.  But sometimes we want to see the
      # structure of the code.
      # vector::size(), std::forward, len(), etc. are not inlined.
      # Also List::List, Tuple2::at0, etc.
      #local opt='-O2'
      local opt='-O0'

      # Do we want DUMB_ALLOC here?
      flags="$CPPFLAGS $opt -g -pg"
      ;;
    *.tcmalloc)
      # when we use tcmalloc, we ave
      flags="$CPPFLAGS -D TCMALLOC"
      link_flags='-ltcmalloc'
      ;;
    *.asan)
      # Note: Clang's ASAN doesn't like DUMB_ALLOC, but GCC is fine with it
      flags="$CPPFLAGS -O0 -g -fsanitize=address"
      ;;
    *.sizelog)
      # debug flags
      flags="$CPPFLAGS -O0 -g -D DUMB_ALLOC -D SIZE_LOG"
      ;;
    *.dbg)
      # debug flags
      flags="$CPPFLAGS -O0 -g"
      ;;
  esac

  # Hack to remove optview::Exec
  case $out in
    *osh_parse*)
      flags="$flags -D OSH_PARSE"
      ;;
    *osh_eval*)
      flags="$flags -D OSH_EVAL"
      ;;
  esac

  # flags are split
  $CXX $flags \
    -I mycpp \
    -I cpp \
    -I _build/cpp \
    -I _devbuild/gen \
    -o $out \
    "$@" \
    $link_flags \
    -lstdc++
}

mycpp-demo() {
  ### Translate, compile, and run a program

  local name=${1:-conditional}

  local raw=_tmp/${name}_raw.cc 
  mycpp $raw mycpp/examples/$name.py

  local cc=_tmp/$name.cc
  example-skeleton $name $raw > $cc

  compile _tmp/$name $cc mycpp/mylib.cc

  # Run it
  _tmp/$name
}

preamble() {
  local name=$1
  cat <<EOF
// $name.cc: translated from Python by mycpp

EOF
}

compile-slice() {
  local name=${1:-osh_parse}
  # Add -opt to make it opt
  local suffix=${2:-.dbg}

  shift 2

  mkdir -p _bin

  # Note: can't use globs here because we have _test.cc
  time compile _bin/$name$suffix _build/cpp/${name}.cc \
    mycpp/mylib.cc \
    cpp/frontend_flag_spec.cc \
    cpp/frontend_match.cc \
    cpp/frontend_tdop.cc \
    cpp/osh_arith_parse.cc \
    cpp/pgen2_parse.cc \
    _build/cpp/runtime_asdl.cc \
    _build/cpp/syntax_asdl.cc \
    _build/cpp/hnode_asdl.cc \
    _build/cpp/id_kind_asdl.cc \
    _build/cpp/consts.cc \
    _build/cpp/arith_parse.cc \
    _build/cpp/arg_types.cc \
    cpp/dumb_alloc.cc \
    cpp/posix.cc \
    cpp/libc.cc \
    "$@"

  #2>&1 | tee _tmp/compile.log
}

compile-slice-opt() {
  local name=${1:-osh_parse}
  compile-slice $name '.opt'

  local opt=_bin/$name.opt
  local stripped=_bin/$name.opt.stripped 
  local symbols=_bin/$name.opt.symbols 

  # As done in the Makefile for Python app bundle
  strip -o $stripped $opt

  # Move the symbols elsewhere and add a link to them.
  if command -v objcopy > /dev/null; then
    objcopy --only-keep-debug $opt $symbols
    objcopy --add-gnu-debuglink=$symbols $stripped
  fi
}

compile-slice-sizelog() { compile-slice "${1:-}" '.sizelog'; }
compile-slice-asan() { compile-slice "${1:-}" '.asan'; }
compile-slice-uftrace() { compile-slice "${1:-}" '.uftrace'; }
compile-slice-tcmalloc() { compile-slice "${1:-}" '.tcmalloc'; }

all-variants() {
  local name=${1:-osh_parse}

  compile-slice $name ''  # .dbg version is default
  compile-slice-opt $name

  compile-slice-sizelog $name
  compile-slice-asan $name
  compile-slice-uftrace $name
  compile-slice-tcmalloc $name

  # show show linking against libasan, libtcmalloc, etc
  ldd _bin/$name*
  echo
  ls -l _bin/$name*
}

readonly TMP=_tmp/mycpp

# TODO: Consolidate this with types/osh-parse-manifest.txt?

# must be generated
  #$REPO_ROOT/core/optview.py 
readonly OSH_PARSE_FILES=(
  $REPO_ROOT/asdl/format.py 
  $REPO_ROOT/asdl/runtime.py 

  $REPO_ROOT/core/alloc.py 
  $REPO_ROOT/frontend/reader.py 
  $REPO_ROOT/frontend/lexer.py 
  $REPO_ROOT/pgen2/grammar.py 
  $REPO_ROOT/pgen2/parse.py 
  $REPO_ROOT/oil_lang/expr_parse.py 
  $REPO_ROOT/oil_lang/expr_to_ast.py 

  $REPO_ROOT/pylib/cgi.py
  # join(*p) is a problem
  #$REPO_ROOT/pylib/os_path.py

  $REPO_ROOT/osh/braces.py

  # This has errfmt.Print() which uses *args and **kwargs
  $REPO_ROOT/core/ui.py

  $REPO_ROOT/core/error.py
  $REPO_ROOT/core/main_loop.py

  $REPO_ROOT/osh/word_.py 
  $REPO_ROOT/osh/bool_parse.py 
  $REPO_ROOT/osh/word_parse.py
  $REPO_ROOT/osh/cmd_parse.py 
  $REPO_ROOT/osh/arith_parse.py 
  $REPO_ROOT/osh/tdop.py
  $REPO_ROOT/frontend/parse_lib.py

  # Note: optview depends on errexit.  But we only need optview::Parse, not
  # optview::exec.
  #$REPO_ROOT/core/state.py
)

readonly CAN_TRANSLATE=(
  # These translate but don't compile
  $REPO_ROOT/osh/glob_.py
  $REPO_ROOT/osh/string_ops.py
  $REPO_ROOT/osh/word_compile.py
  $REPO_ROOT/osh/builtin_bracket.py
  $REPO_ROOT/osh/split.py
  $REPO_ROOT/oil_lang/regex_translate.py
)


readonly TRANSLATE=(
  # Format strings not constant, in PrintRequired
  #$REPO_ROOT/core/comp_ui.py
  #$REPO_ROOT/osh/split.py

  #$REPO_ROOT/osh/word_compile.py
  #$REPO_ROOT/osh/glob_.py
  #$REPO_ROOT/osh/string_ops.py

  #$REPO_ROOT/osh/sh_expr_eval.py

  #$REPO_ROOT/osh/word_eval.py
  #$REPO_ROOT/core/state.py

  #$REPO_ROOT/osh/cmd_exec.py
)

# From types/more-oil-manifest.txt
readonly MORE_OIL=(
  $REPO_ROOT/osh/glob_.py  # translates pretty well
  $REPO_ROOT/osh/string_ops.py  # translation problems
  $REPO_ROOT/frontend/location.py

  # fails because of readline_mod return value
  #$REPO_ROOT/osh/history.py

  # fails because of multiple exceptions in libc.wcswidth
  # maybe change both to RuntimeError?
  # except (SystemError, UnicodeError):
  #$REPO_ROOT/core/comp_ui.py

  $REPO_ROOT/osh/word_compile.py  # translates well
  $REPO_ROOT/osh/builtin_bracket.py

  # core/main_loop.py causes a lot of problems

  $REPO_ROOT/osh/split.py
  $REPO_ROOT/oil_lang/regex_translate.py

  # Fails because of Union[None, bool, str] -- dynamic typing
  #$REPO_ROOT/frontend/args.py
)

osh-parse() {
  local name=${1:-osh_parse}

  local tmp=$TMP
  mkdir -p $tmp

  local raw=$tmp/${name}_raw.cc 

  #if false; then
  if true; then
    mycpp $raw bin/$name.py "${OSH_PARSE_FILES[@]}" #"${TRANSLATE[@]}"
      #"${MORE_OIL[@]}"
  fi

  local cc=_build/cpp/$name.cc

  { preamble $name
    cpp-skeleton $name $raw 
  } > $cc

  compile-slice $name '.dbg'
}

osh-eval() {
  ### Translate bin/osh_eval.py

  local name=${1:-osh_eval}

  local tmp=$TMP
  mkdir -p $tmp

  local raw=$tmp/${name}_raw.cc 

  #if false; then
  if true; then
    # relies on splitting
    # _devbuild is ASDL stuff
    # frontend metaprogramming:
    #   lexer_def.py 
    #   match.py is cpp/
    #   id_kind_def.py
    # core/meta.py
    # core/process.py - not ready
    # pyutil.py -- Python only (Resource Loader, etc.)
    # core/util.py -- not ready
    # os_path.py: crashes on path += '/' + b
    # pgen2/parse.py: prefer hand-written C

    local exclude='_devbuild/|pybase.py|optview.py|option_def.py|id_kind_def.py|match.py|lexer_def.py|/meta.py|pretty.py|process.py|pyerror.py|pyutil.py|util.py|os_path.py|path_stat.py|bool_stat.py|passwd.py|builtin_def.py|consts.py|pgen2/parse.py|oil_lang/objects.py|flag_spec.py|flag_def.py|builtin_process'

    # TODO: Should we have a --header-file option?
    # And then list the classes and functions that have to be exported
    # or a regex
    #
    # ColorOutput|_Action
    # Or the modules like asdl_runtime.h

    mycpp $raw $(egrep -v "$exclude" types/osh-eval-manifest.txt)
  fi

  local cc=_build/cpp/$name.cc

  { preamble $name
    cpp-skeleton $name $raw 
  } > $cc

  compile-slice 'osh_eval' '.dbg'
}

asdl-runtime() {
  ### Translate ASDL deps for unit tests

  local name=asdl_runtime
  local raw=_tmp/mycpp/${name}_raw.cc 

  mycpp $raw $REPO_ROOT/{asdl/runtime,asdl/format,core/ansi,pylib/cgi,qsn_/qsn}.py 

  local cc=asdl/runtime.cc

  { cat <<EOF
// asdl/runtime.cc: This file generated by mycpp from asdl/{runtime,format}.py

#include "mylib.h"
#include "hnode_asdl.h"
#include "qsn_qsn.h"

// For hnode::External in asdl/format.py.  TODO: Remove this when that is removed.
inline Str* repr(void* obj) {
  assert(0);
}

EOF
    cat $raw
  } > $cc

  #compile-slice $name '.dbg'
}

osh-parse-asan() {
  ### Wrapper for ASAN env vars, to show stack strace

  _bin/osh_parse.asan "$@"
}

osh-eval-asan() {
  ### Wrapper for ASAN env vars, to show stack strace

  _bin/osh_eval.asan "$@"
}

size-profile() {
  wc -l _build/cpp/osh_parse.cc

  local bin=_bin/osh_parse.opt

  ls -l _bin/osh_parse*

  bloaty -d compileunits $bin
  echo
  bloaty -d symbols $bin
}

smoke-manifest() {
  for file in */*.sh; do
  #for file in spec/*.sh; do
    case $file in
      # Exclude _tmp/ etc.
      _*) continue ;;

      # the STDOUT blocks have invalid syntax
      # TODO: Enable this as a separate test of syntax errors
      #spec/*) continue ;;

      # pgen2 not done
      spec/oil-*) continue ;;
      spec/arith-context.test.sh) continue ;;
      spec/builtin-eval-source.test.sh) continue ;;

      # This has Oil syntax
      test/oil-runtime-errors.sh) continue ;;
    esac

    echo $file
  done
}

py-parse() {
  local id=$1
  local file=$2

  local out=_tmp/osh-parse-smoke/py/$id
  bin/osh --ast-format text -n $file > $out
}

cpp-parse() {
  local id=$1
  local file=$2

  local out=_tmp/osh-parse-smoke/cpp/$id
  _bin/osh_parse.asan $file > $out
}

dump-asts() {
  ### Dump ASTs produced by Python and C++ 

  local manifest='_tmp/smoke-manifest.txt'

  # TODO: make the first 10 match

  # nl gives the ID
  smoke-manifest | nl > $manifest

  rm -f _tmp/osh-parse-smoke/{py,cpp}/*
  mkdir -p _tmp/osh-parse-smoke/{py,cpp}

  set +o errexit
  time cat $manifest | xargs --verbose -n 2 -- $0 py-parse
  time cat $manifest | xargs --verbose -n 2 -- $0 cpp-parse
  set -o errexit
}

compare-asts() {
  mkdir -p _tmp/osh-parse-smoke/{py,cpp,diff}

  local num_failed=0
  for path in _tmp/osh-parse-smoke/py/*; do
    echo $path
    local diff_path=${path//py/diff}
    set +o errexit
    diff -u $path ${path//py/cpp} > $diff_path
    local status=$?
    set -o errexit
    if test $status -ne 0; then
      num_failed=$((num_failed + 1))
    fi

  done

  echo "$num_failed differences"
}

osh-parse-smoke() {
  ### Run C++ version bin/osh_parse on our shell scripts (with ASAN on)

  local python=${1:-}

  local parse_errors=''
  local crashed=''

  while read file; do
    set +o errexit

    echo "_____ $file"

    if test -n "$python"; then
      bin/osh -n $file | wc -l
    else
      local osh_parse=_bin/osh_parse.asan 
      $osh_parse $file | wc -l

      # This also works
      #local osh_eval=_bin/osh_eval.asan 
      #$osh_eval -n $file | wc -l
    fi

    case $? in
      0)
        ;;
      2)
        parse_errors+=" $file"
        ;;
      *)
        crashed+=" $file"
        ;;
    esac

    set -o errexit
  done < <(smoke-manifest)

  echo
  echo "Can't parse:"
  echo
  for file in $parse_errors; do  # split words
    echo $file
  done

  # A couple spec tests fail because they have what looks like Oil expressions
  echo
  echo 'CRASHED:'
  echo
  for file in $crashed; do  # split words
    echo $file
  done
}

osh-eval-smoke() {
  ### Run osh_eval.dbg over a bunch of shell scripts

  # Problem: all while loops go infinitely now...

  local parse_errors=''
  local fail=''

  for file in spec/[01a]*.sh; do
    set +o errexit

    echo "_____ $file"

    local osh_eval=_bin/osh_eval.dbg
    $osh_eval $file

    case $? in
      0)
        ;;
      2)
        parse_errors+=" $file"
        ;;
      *)
        fail+=" $file"
        ;;
    esac

    set -o errexit
  done

  echo
  echo "Can't parse:"
  echo
  for file in $parse_errors; do  # split words
    echo $file
  done

  # A couple spec tests fail because they have what looks like Oil expressions
  echo
  echo 'FAILED:'
  echo
  for file in $fail; do  # split words
    echo $file
  done
}

osh-eval-demo() {
  types/oil-slice.sh demo _bin/osh_eval.dbg
}

#
# Public
#

# Used by devtools/release.sh and devtools/release-native.sh
# This is the demo we're releasing to users!
compile-oil-native() {
  compile-slice osh_eval ''
}

compile-oil-native-opt() {
  compile-slice-opt osh_eval ''
}

compile-oil-native-asan() {
  compile-slice-asan osh_eval ''
}

# Demo for the oil-native tarball.
tarball-demo() {
  mkdir -p _bin

  time compile-oil-native-opt

  local bin=_bin/osh_eval.opt.stripped
  ls -l $bin

  echo
  echo "You can now run $bin.  Example:"
  echo

  set -o xtrace
  $bin -n -c 'echo "hello $name"'
}


if test $(basename $0) = 'mycpp.sh'; then
  "$@"
fi

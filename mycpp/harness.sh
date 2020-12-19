# harness.sh: Allow customization of compile/build/run for each example.

EXAMPLES=( $(cd examples && echo *.py) )
EXAMPLES=( "${EXAMPLES[@]//.py/}" )

gen-main() {
  local main_module=${1:-fib_iter}
  cat <<EOF

int main(int argc, char **argv) {
  // gc_heap::gHeap.Init(1 << 10);  // for debugging
  gc_heap::gHeap.Init(512);
  // gc_heap::gHeap.Init(128 << 10);  // 128 KiB; doubling in size
  // gc_heap::gHeap.Init(400 << 20);  // 400 MiB to avoid garbage collection

  if (getenv("BENCHMARK")) {
    fprintf(stderr, "Benchmarking...\n");
    $main_module::run_benchmarks();
  } else {
    $main_module::run_tests();
  }
}
EOF
}

cpp-skeleton() {
  local main_module=${1:-fib_iter}
  shift

  cat <<EOF
// examples/$main_module

EOF

  # the raw module
  cat "$@"

  # main() function
  gen-main $main_module
}

typecheck-example() {
  local name=$1
  if test "$(type -t typecheck-$name)" = "function"; then
    typecheck-$name
  else
    mypy --py2 --strict examples/$name.py
  fi
}

_translate-example() {
  local name=${1:-fib}
  local variant=${2:-}

  local main="examples/$name.py"

  mkdir -p _gen

  local raw=_gen/${name}_raw${variant}.cc
  local out=_gen/${name}${variant}.cc

  # NOTE: mycpp has to be run in the virtualenv, as well as with a different
  # PYTHONPATH.
  ( source _tmp/mycpp-venv/bin/activate
    # flags may be empty
    time PYTHONPATH=$MYPY_REPO ./mycpp_main.py $main > $raw
  )
  wc -l $raw

  local main_module=$(basename $main .py)
  cpp-skeleton $main_module $raw > $out

  #wc -l _gen/*

  echo
  #cat $out
  echo "Wrote $out"
}

translate-example() {
  local name=$1
  # e.g. translate-modules and compile-modules are DIFFERENT.

  if test "$(type -t translate-$name)" = "function"; then
    translate-$name
  else
    _translate-example "$@"  # name and optional variant
  fi
}

_compile-example() { 
  local name=${1:-fib} #  name of output, and maybe input
  local variant=${2:-}

  local src=_gen/$name.cc

  # TODO: Remove for performance?
  local flags='-D GC_PROTECT '

  # to see what happened
  flags+='-D GC_DEBUG '

  case $variant in
    (asan)
      flags+="$CXXFLAGS $ASAN_FLAGS"
      ;;
    (opt)
      flags+="$CXXFLAGS -O2 -g"
      ;;
    (*)
      flags+="$CXXFLAGS"
      ;;
  esac

  local out=_bin/${name}.${variant}
  mkdir -p _bin

  local -a runtime
  if test -n "${GC:-}"; then
    runtime=(my_runtime.cc mylib2.cc gc_heap.cc)
  else
    runtime=(mylib.cc gc_heap.cc)
  fi

  echo "__ Compiling with $CXX"

  # need -lstdc++ for 'operator new'
  # set -x
  $CXX -o $out $flags -I . "${runtime[@]}" $src -lstdc++
}

compile-example() {
  local name=$1
  local variant=$2

  if test "$(type -t compile-$name)" = "function"; then
    compile-$name $variant
  else
    _compile-example $name $variant
  fi
}

pyrun-example() {
  local name=$1
  if test "$(type -t pyrun-$name)" = "function"; then
    pyrun-$name
  else
    examples/${name}.py
  fi
}

mycpp-main() {
  ( source _tmp/mycpp-venv/bin/activate
    time PYTHONPATH=$MYPY_REPO MYPYPATH=$REPO_ROOT:$REPO_ROOT/native \
      ./mycpp_main.py "$@"
  )
}

cgi-header() {
  local name=${1:-cgi}

  if true; then
    mycpp-main \
      --header-out _gen/cgi.h \
      --to-header cgi \
      examples/cgi.py > _gen/cgi_raw.cc
  fi

  wc -l _gen/cgi.*
  ls -l _gen/cgi.*

  # Add main() function
  { cat _gen/cgi_raw.cc
    gen-main cgi
  } > _gen/cgi.cc

  _compile-example cgi
  ls -l _bin/cgi
}


#
# All
#

typecheck-all() {
  for name in "${EXAMPLES[@]}"; do
    if should-skip $name; then
      continue
    fi

    echo "___ $name"
    typecheck-example $name
  done
}


build-all() {
  rm -v -f _bin/* _gen/*
  for name in "${EXAMPLES[@]}"; do
    if should-skip $name; then
      continue
    fi

    echo -----
    echo "EXAMPLE $name"
    echo -----

    translate-example $name
    compile-example $name asan
    compile-example $name opt
  done
}

test-all() {
  mkdir -p _tmp

  if test $# -eq 0; then
    readonly cases=("${EXAMPLES[@]}")
  else
    # Explicit list passed
    readonly cases=("$@")
  fi

  time for name in "${cases[@]}"; do
    if should-skip $name; then
      echo "  (skipping $name)"
      continue
    fi

    echo -n "___ $name"

    pyrun-example ${name} > _tmp/$name.python.txt 2>&1
    _bin/$name.asan > _tmp/$name.cpp.txt 2>&1

    diff-output $name
  done
}

diff-output() {
  local name=$1
  if diff -u _tmp/$name.{python,cpp}.txt > _tmp/$name.diff.txt; then
    echo $'\t\t\tOK'
  else
    echo $'\t\tFAIL'
    cat _tmp/$name.diff.txt
  fi
}

benchmark-all() {
  # TODO: change this to iterations
  # BENCHMARK_ITERATIONS=1

  export BENCHMARK=1

  local out_dir=../_tmp/mycpp-examples/raw
  mkdir -p $out_dir
  local out=$out_dir/times.tsv

  # Create a new TSV file every time, and then append rows to it.

  # TODO:
  # - time.py should have a --header flag to make this more readable?
  # - More columns: -O1 -O2 -O3, machine, iterations of benchmark.
  echo $'status\telapsed_secs\tuser_secs\tsys_secs\tmax_rss_KiB\texample_name\tlanguage' > $out

  readonly -a time=(time-tsv --rusage --append -o $out)

  for name in "${EXAMPLES[@]}"; do
    if should-skip-benchmark $name; then
      echo "  (skipping $name)"
      continue
    fi

    echo "___ $name"

    echo
    echo $'\t[ C++ ]'
    "${time[@]}" --field $name --field 'C++' -- _bin/$name.opt

    echo
    echo $'\t[ Python ]'
    "${time[@]}" --field $name --field 'Python' -- $0 pyrun-example $name
  done

  cat $out
}

#
# List of examples
#

should-skip() {
  case $1 in
    # not passing yet!
    # Other problematic constructs: **kwargs, named args

    # TODO:
    # - alloc_main and lexer_main work!  They just need build scripts
    # - varargs calls p_die() which aborts
    (pgen2_demo|alloc_main|lexer_main|named_args|varargs)
      return 0
      ;;

    (strings)  # '%5d' doesn't work yet.  TODO: fix this.
      return 0
      ;;

    (parse)
      # TODO. expr.asdl when GC=1
      # qsn_qsn.h is incompatible
      return 0;
      ;;
  esac

  return 1
}

should-skip-benchmark() {
  case $1 in
    (test_*)
      return 0  # nope, nothing interesting here
      ;;

    (control_flow)
      # TODO: fix 8191 exceptions problem, I think caused by Alloc<ParseError>
      return 0
      ;;
  esac

  should-skip $1  # return this
}

#
# One
#

readonly -a TIME_xUM=(/usr/bin/time --format '%x %U %M')

example-both() {
  local name=$1
  local variant=${2:-asan}

  typecheck-example $name

  translate-example $name
  compile-example $name $variant

  # We're asserting both stdout and stderr, so use a temp file

  local tmp='_tmp/t'

  # diff stderr too!
  echo
  echo $'\t[ C++ ]'
  set +o errexit
  "${TIME_xUM[@]}" -o $tmp -- _bin/$name.$variant > _tmp/$name.cpp.txt 2>&1
  set -o errexit
  cat $tmp

  #time _bin/$name.$variant > _tmp/$name.cpp.txt 2>&1

  echo
  echo $'\t[ Python ]'
  set +o errexit
  "${TIME_xUM[@]}" -o $tmp -- $0 pyrun-example $name > _tmp/$name.python.txt 2>&1
  set -o errexit
  cat $tmp

  #time $0 pyrun-example $name > _tmp/$name.python.txt 2>&1

  diff-output $name
}

benchmark-both() {
  local name=$1

  export BENCHMARK=1
  example-both $name opt
}

strip-all() {
  for bin in _bin/*; do
    case $bin in
      *.stripped)
        continue
        ;;
      *)
        if test -f $bin.stripped; then
          echo "$bin already stripped"
          continue
        fi

        strip -o $bin.stripped $bin
        ;;
    esac
  done

  ls -l _bin/*.stripped
}

# This is a preview for what benchmarks/compute will do.
fib-compare() {
  # 6768 KiB
  "${TIME_xUM[@]}" ../benchmarks/compute/fib.py 

  # 1652 KiB
  "${TIME_xUM[@]}" ../benchmarks/compute/fib.sh

  # 1652 KiB
  "${TIME_xUM[@]}" dash ../benchmarks/compute/fib.sh 

  # Measurement error!!!
  # But we're passing resource.RUSAGE_CHILDREN?
  ../benchmarks/time_.py -o /dev/stdout --rusage -- dash ../benchmarks/compute/fib.sh

  # With OSH we're getting down to 2000-3000 KiB now?
}

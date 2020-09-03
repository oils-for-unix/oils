# harness.sh: Allow customization of compile/build/run for each example.

EXAMPLES=( $(cd examples && echo *.py) )
EXAMPLES=( "${EXAMPLES[@]//.py/}" )

gen-main() {
  local main_module=${1:-fib_iter}
  cat <<EOF

int main(int argc, char **argv) {
  if (getenv("BENCHMARK")) {
    fprintf(stderr, "Benchmarking...\n");
    $main_module::run_benchmarks();
  } else {
    $main_module::run_tests();
  }
}
EOF
}

filter-cpp() {
  local main_module=${1:-fib_iter}
  shift

  cat <<EOF
#include "mylib.h"

EOF

  cat "$@"

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

  flags=''
  case $variant in
    (.shared_ptr)
      flags='--shared-ptr'
      ;;
  esac

  # NOTE: mycpp has to be run in the virtualenv, as well as with a different
  # PYTHONPATH.
  ( source _tmp/mycpp-venv/bin/activate
    # flags may be empty
    time PYTHONPATH=$MYPY_REPO ./mycpp_main.py $flags $main > $raw
  )
  wc -l $raw

  local main_module=$(basename $main .py)
  filter-cpp $main_module $raw > $out

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

  local src=_gen/$name${variant}.cc

  # for benchmarks, and to debug crashes
  local more_flags='-O2 -g'
  #local more_flags=''

  local out=_bin/${name}${variant}
  mkdir -p _bin

  # need -lstdc++ for 'operator new'
  $CXX -o $out $CPPFLAGS $more_flags -I . \
    mylib.cc $src -lstdc++
}

compile-example() {
  local name=$1
  if test "$(type -t compile-$name)" = "function"; then
    compile-$name
  else
    _compile-example "$@"  # name and optional variant
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
    compile-example $name
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
    _bin/$name > _tmp/$name.cpp.txt 2>&1

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
    "${time[@]}" --field $name --field 'C++' -- _bin/$name

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
      return 0;
      ;;
  esac

  return 1
}

should-skip-benchmark() {
  case $1 in
    (hoist|conditional|switch_)
      return 0  # nope, nothing interesting here
      ;;
  esac

  should-skip $1  # return this
}

#
# One
#

example-both() {
  local name=$1

  typecheck-example $name

  translate-example $name
  compile-example $name

  # Doesn't work
  if false; then
    translate-example $name .shared_ptr
    compile-example $name .shared_ptr
  fi

  # Not great because of stdout
  #local -a time=(/usr/bin/time --format '%U %M' --)

  # diff stderr too!
  echo
  echo $'\t[ C++ ]'
  #"${time[@]}" _bin/$name > _tmp/$name.cpp.txt 2>&1
  time _bin/$name > _tmp/$name.cpp.txt 2>&1

  echo
  echo $'\t[ Python ]'
  #"${time[@]}" $0 pyrun-example $name > _tmp/$name.python.txt 2>&1
  time $0 pyrun-example $name > _tmp/$name.python.txt 2>&1

  diff-output $name
}

benchmark-both() {
  export BENCHMARK=1
  example-both "$@"
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



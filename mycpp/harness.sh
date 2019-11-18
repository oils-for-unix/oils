# harness.sh: Allow customization of compile/build/run for each example.

EXAMPLES=( $(cd examples && echo *.py) )
EXAMPLES=( "${EXAMPLES[@]//.py/}" )

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
  local main="examples/$name.py"

  mkdir -p _gen

  local raw=_gen/${name}_raw.cc
  local out=_gen/${name}.cc

  # NOTE: mycpp has to be run in the virtualenv, as well as with a different
  # PYTHONPATH.
  ( source _tmp/mycpp-venv/bin/activate
    time PYTHONPATH=$MYPY_REPO ./mycpp_main.py $main > $raw
  )
  wc -l $raw

  local main_module=$(basename $main .py)
  filter-cpp $main_module $raw > $out

  wc -l _gen/*

  echo
  cat $out
}

translate-example() {
  local name=$1

  # e.g. translate-modules and compile-modules are DIFFERENT.

  if test "$(type -t translate-$name)" = "function"; then
    translate-$name
  else
    _translate-example $name
  fi
}

_compile-example() { 
  local name=${1:-fib} #  name of output, and maybe input
  local src=${2:-_gen/$name.cc}

  # need -lstdc++ for operator new

  local more_flags='-O0 -g'  # to debug crashes
  #local more_flags=''
  mkdir -p _bin
  $CXX -o _bin/$name $CPPFLAGS $more_flags -I . \
    mylib.cc $src -lstdc++
}

compile-example() {
  local name=$1
  if test "$(type -t compile-$name)" = "function"; then
    compile-$name
  else
    _compile-example $name
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

    if diff -u _tmp/$name.{python,cpp}.txt > _tmp/$name.diff.txt; then
      echo $'\t\t\tOK'
    else
      echo $'\t\tFAIL'
      cat _tmp/$name.diff.txt
    fi
  done
}

benchmark-all() {
  # TODO: change this to iterations
  # BENCHMARK_ITERATIONS=1

  export BENCHMARK=1

  local out=_tmp/mycpp-examples.tsv

  # Create a new TSV file every time, and then append rows to it.

  # TODO:
  # - time.py should have a --header flag to make this more readable?
  # - More columns: -O1 -O2 -O3, machine, iterations of benchmark.
  echo $'status\tseconds\texample_name\tlanguage' > $out

  for name in "${EXAMPLES[@]}"; do
    if should-skip $name; then
      echo "  (skipping $name)"
      continue
    fi

    echo "___ $name"

    echo
    echo $'\t[ C++ ]'
    time-tsv -o $out --field $name --field 'C++' -- _bin/$name

    echo
    echo $'\t[ Python ]'
    time-tsv -o $out --field $name --field 'Python' -- $0 pyrun-example $name
  done

  cat $out
}

#
# List of examples
#

should-skip() {
  case $1 in
    # not passing yet!
    #
    # - later
    #   - scoped_resource: Not translated at all.  No RuntimeError.

    # Other problematic constructs: **kwargs, named args

    # TODO:
    # - alloc_main and lexer_main work!  They just need build scripts
    # - varargs doesn't have p_die()
    pgen2_demo|alloc_main|lexer_main|named_args|varargs)
      return 0
      ;;

    scoped_resource)
      return 0
      ;;
    *)
      return 1
  esac
}

#
# One
#

example-both() {
  local name=$1

  typecheck-example $name
  translate-example $name
  compile-example $name

  echo
  echo $'\t[ C++ ]'
  time _bin/$name

  echo
  echo $'\t[ Python ]'
  time pyrun-example $name
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



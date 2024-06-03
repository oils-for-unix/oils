# Datalog

The files in this directory are [Souffle](https://souffle-lang.github.io/)
programs. We use them for to peform dataflow analyses on the Python -> C++
translation.

See the [Souffle Language Reference](https://souffle-lang.github.io/program) for
details on how to write datalog.

## Installing Souffle

```
deps/from_tar.sh download-souffle
deps/from_tar.sh extract-souffle
deps/from_tar.sh build-souffle
```

## Compiling a Souffle Binary

You can compile a souffle program to fast native code with the `souffle_binary`
ninja rule. For example, `souffle_binary('mycpp/datalog/call-graph.dl')` will
produce an executable called `_bin/tools/call-graph`.

See this [page from the Souffle docs](https://souffle-lang.github.io/execute)
for details about how to run your program.

## Our Analyses

TBD

# Usage:
#   source mycpp/ninja.sh <function name>

# TODO: Get these from Ninja

readonly -a OLDSTL_RUNTIME=(
    mycpp/oldstl_containers.cc
    mycpp/leaky_builtins.cc
    mycpp/leaky_containers.cc
)

readonly -a GC_RUNTIME=(
    mycpp/gc_builtins.cc
    mycpp/gc_heap.cc
    mycpp/gc_mylib.cc
    mycpp/leaky_builtins.cc
    mycpp/leaky_containers.cc
)


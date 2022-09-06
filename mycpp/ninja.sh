# Usage:
#   source mycpp/ninja.sh

# TODO: Get from Ninja

readonly -a GC_RUNTIME=(
    # mycpp/gc_heap.cc
    mycpp/cheney_heap.cc
    mycpp/marksweep_heap.cc
    mycpp/gc_mylib.cc
    mycpp/leaky_builtins.cc
    mycpp/leaky_containers.cc
    mycpp/leaky_mylib.cc
)


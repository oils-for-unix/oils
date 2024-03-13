Oils for Unix
=============

Oils is a small tool that unifies shell, Python, regexes, JSON, and YAML.  It's
our upgrade path from bash to a better language and runtime!  

    https://www.oilshell.org/

This is fast shell in C++, completed in 2024.  Its source code is generated
from a reference implementation in Python, but it relies on no Python code.

To use it, run:

    ./configure     # detects whether GNU readline is installed, etc.

    _build/oils.sh  # builds optimized binary

    sudo ./install
    
All you need is a C++ compiler.

Then try:

    osh -c 'echo hi'    

    osh -n -c 'echo hi'  # parse a script

    ysh -c 'json write ({foo: 42})'

Feedback:

    https://github.com/oilshell/oil/issues


More build configuration
------------------------

You can pass the compiler and build variant to _build/oils.sh:

    _build/oils.sh ~/install/cosmocc/bin/cosmoc++ dbg

The default values are 'cxx' (c++ system compiler), and 'opt' (optimized build)

You can also override the variables documented at the top of
build/ninja-rules-cpp.sh (e.g. BASE_CXXFLAGS, CXXFLAGS)


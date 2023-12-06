Oils for Unix
=============

This is the pure C++ tarball for Oils.  (In contrast to the "executable spec",
it has no CPython code).

To use it, run

    ./configure     # detects whether GNU readline is installed, etc.

    _build/oils.sh  # builds optimized binary

    sudo ./install
    
All you need is a C++ compiler.

Then try:

    osh -c 'echo hi'    

    osh -n -c 'echo hi'  # parse a script

Send feedback to:

    https://github.com/oilshell/oil/issues

(TODO: Replace this with INSTALL.txt)


## More build configuration

You can pass the compiler and build variant to _build/oils.sh:

    _build/oils.sh ~/install/cosmocc/bin/cosmoc++ dbg

The default values are 'cxx' (c++ system compiler), and 'opt' (optimized build)

You can also override the variables documented at the top of
build/ninja-rules-cpp.sh (e.g. BASE_CXXFLAGS, CXXFLAGS)


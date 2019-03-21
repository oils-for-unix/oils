# hello.mk: For the demo hello app.

# C module dependencies
-include _build/hello/ovm.d

# What Python module to run.
_build/hello/main_name.c:
	$(ACTIONS_SH) main-name hello hello.ovm > $@

# for typing module
HELLO_PYPATH := $(REPO_ROOT)/build/testdata:$(REPO_ROOT)/vendor

# Dependencies calculated by importing main.  The guard is because ovm.d
# depends on it.  Is that correct?  We'll skip it before 'make dirs'.
_build/hello/app-deps-%.txt: $(HELLO_SRCS) \
	_build/detected-config.sh build/app_deps.py
	test -d _build/hello && \
	  $(ACTIONS_SH) app-deps hello $(HELLO_PYPATH) hello

_build/hello/py-to-compile.txt: \
	_build/detected-config.sh build/app_deps.py
	test -d _build/hello && \
	  $(ACTIONS_SH) py-to-compile $(HELLO_PYPATH) hello > $@

# NOTE: We could use src/dest paths pattern instead of _build/app?
#
# TODO:
# - Deps need to be better.  Depend on .pyc and .py.    I guess
#   app-deps hello will compile the .pyc files.  Don't need a separate action.
#   %.pyc : %py

HELLO_BYTECODE_DEPS := \
	build/testdata/hello-version.txt \
        _build/release-date.txt \
	build/testdata/hello-manifest.txt

_build/hello/bytecode-cpython.zip: $(HELLO_SRCS) $(HELLO_BYTECODE_DEPS) \
                           _build/hello/app-deps-cpython.txt
	{ echo 'build/testdata/hello-version.txt hello-version.txt'; \
	  echo '_build/release-date.txt release-date.txt'; \
	  cat build/testdata/hello-manifest.txt \
	      _build/hello/app-deps-cpython.txt \
	} | build/make_zip.py $@

_build/hello/bytecode-opy.zip: $(HELLO_SRCS) $(HELLO_BYTECODE_DEPS) \
                           _build/hello/opy-app-deps.txt
	{ echo 'build/testdata/hello-version.txt hello-version.txt'; \
	  echo '_build/release-date.txt release-date.txt'; \
	  cat build/testdata/hello-manifest.txt \
	      _build/hello/opy-app-deps.txt; \
	} | build/make_zip.py $@

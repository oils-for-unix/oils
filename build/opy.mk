# opy.mk: Portable build rulesf or OPy.

# TODO:
# - Grammar
# - We don't need a configure script?
# - build/oil.mk and build/hello.mk?
#
# Use release-date I guess?

-include _build/opy/ovm.d

_build/opy/py27.grammar.pickle:
	bin/opyc pgen2 opy/py27.grammar $@

_build/opy/main_name.c:
	$(ACTIONS_SH) main-name bin.opy_ opy.ovm > $@

_build/opy/app-deps-%.txt: _build/detected-config.sh build/app_deps.py
	test -d _build/opy && \
	  $(ACTIONS_SH) app-deps opy $(REPO_ROOT) bin.opy_

_build/opy/py-to-compile.txt: _build/detected-config.sh build/app_deps.py
	test -d _build/opy && \
	  $(ACTIONS_SH) py-to-compile $(REPO_ROOT) bin.opy_ > $@


# TODO: oil-version can be like this too.
GRAMMAR = _build/opy/py27.grammar.pickle

OPY_BYTECODE_DEPS := \
	_build/release-date.txt \
	build/opy-manifest.txt \
	$(GRAMMAR)

# NOTE: runpy deps are included in opy-app-deps.txt.
_build/opy/bytecode-opy-manifest.txt: \
	$(OPY_BYTECODE_DEPS) _build/opy/opy-app-deps.txt
	{ echo '_build/release-date.txt release-date.txt'; \
	  echo $(GRAMMAR) $(GRAMMAR); \
	  cat build/opy-manifest.txt \
	      _build/opy/opy-app-deps.txt; \
	  $(ACTIONS_SH) pyc-version-manifest $@; \
	} > $@

_build/opy/bytecode-%.zip: _build/opy/bytecode-%-manifest.txt
	build/make_zip.py $@ < $^

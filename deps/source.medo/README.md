source.medo
===========

Add these files:


    deps/source.medo
      wild-corpus/
        2023-03-02.treeptr  # not a WEDGE because it doesn't need to be built.
                            # But it is versioned
      mypy/
        0.780.treeptr       # uses 'git' , not 'tar'

      mypy-venv/            # depends on mypy-0.780
        WEDGE
        - I guess it's relative and goes in ~/wedge/oils-for-unix.org/mypy-venv/0..780 ?

- Or is it possible to put them both in a sidecar?  LIke wild-corpus 
  - `~/git/oilshell/oil_DEPS/`
  - `~/git/oilshell/oil2_DEPS/`
  - Reference with `../$(basename $REPO_ROOT)_DEPS/`
  - But then the data is duplicated






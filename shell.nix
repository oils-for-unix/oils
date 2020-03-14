# Nix shell expression for the oil shell (formatted with nixfmt)
#   Note: run `nixfmt shell.nix` in nix-shell to reformat in-place
#
# By default fetch the most-recent 19.09 version of the stable NixOS release.
# This should be fine, but if it causes trouble it can be pinned to ensure
# everyone is running exactly the same versions.
{ nixpkgs ? fetchTarball "channel:nixos-19.09", dev ? "all", test ? "smoke"
, cleanup ? true }:

let
  # Import the package set.
  pkgs = import nixpkgs { };

  # Added the following 3 declarations (and parameters/defaults above) to
  # demonstrate how you could make the behavior a little configurable.
  #
  # By default, it will run:
  # - "all" dev build (--argstr dev minimal or none to disable)
  # - the "smoke" tests (--argstr test osh-all or none to disable)
  # - and clean on exit (ex: --argstr cleanup none to disable)
  build_oil = if dev == "none" then
    "echo Skipping Oil build."
  else ''
    echo Building \'${dev}\' Oil.
    "$PWD/build/dev.sh" ${dev}
  '';
  test_oil = if test == "none" then
    "echo Skipping Oil tests."
  else ''
    echo Running Oil \'${test}\' tests.
    "$PWD/test/spec.sh" ${test}
  '';
  cleanup_oil = if cleanup == "none" then ''
    echo "Note: nix-shell will *NOT* clean up Oil dev build on exit!"
    trap 'echo "NOT cleaning up Oil dev build."' EXIT
  '' else ''
    echo "Note: nix-shell will clean up the dev build on exit."
    trap 'echo "Cleaning up Oil dev build."; "$PWD/build/dev.sh" clean' EXIT
  '';
in with pkgs;

let
  # Most of the items you listed in #513 are here now. I'm not sure what the
  # remaining items here mean, so I'm not sure if they're covered.
  #
  # static analysis
  #   mypy library for mycpp
  # benchmarks
  #   ocaml configure, etc. This is just source though.
  # C deps
  #   python headers for bootstrapping
  # big one: Clang for ASAN and other sanitizers (even though GCC has some)
  #   Clang for coverage too

  # nixpkgs: busybox linux only; no smoosh
  # could append something like: ++ lib.optionals stdenv.isLinux [ busybox ]
  spec_tests = [ bash dash mksh zsh busybox ];

  static_analysis = [
    mypy # This is the Python 3 version
    (python2.withPackages (ps: with ps; [ flake8 pyannotate ]))
    # python3Packages.black # wink wink :)
  ];

  binary = [ re2c ];
  doctools = [ cmark ];
  c_deps = [ readline ];

  shell_deps = [
    gawk
    time
    # additional command dependencies I found as I went
    # guessing they go here...
    # run with nix-shell --pure to make missing deps easier to find!
    file
    git
    hostname
    which
  ];

  nix_deps = [
    nixfmt # `nixfmt shell.nix` to format in place
  ];

  # Create a shell with packages we need.
in mkShell rec {

  buildInputs = c_deps ++ binary ++ spec_tests ++ static_analysis ++ doctools
    ++ shell_deps ++ nix_deps ++ doctools;

  # Not sure if this is "right" (for nix, other platforms, etc.)
  # doctools/cmark.py hardcoded /usr/local/lib/libcmark.so, and it looks
  # like Nix has as much trouble with load_library as you have. For a
  # "build" I think we'd use a patchPhase to replace the hard path
  # in cmark.py with the correct one. Since we can't patch the source here
  # I'm hacking an env in here and in cmark.py. Hopefully others will
  # weigh in if there's a better way to handle this.
  #
  # Note: Nix automatically adds identifiers declared here to the environment!
  _NIX_SHELL_LIBCMARK = "${cmark}/lib/libcmark${stdenv.hostPlatform.extensions.sharedLibrary}";

  # Need nix to relax before it'll link against a local file.
  NIX_ENFORCE_PURITY = 0;

  # Note: failing spec test with either of these LOCALE_ARCHIVE settings.
  #
  # $ test/spec.sh oil-options -r 0 -v
  # if libc.fnmatch(pat_val.s, to_match):
  #  SystemError: Invalid locale for LC_CTYPE
  LOCALE_ARCHIVE =
    if stdenv.isLinux then "${glibcLocales}/lib/locale/locale-archive" else "";

  # a different option:
  # LOCALE_ARCHIVE = lib.optionalString (stdenv.hostPlatform.libc == "glibc") "${glibcLocales}/lib/locale/locale-archive";

  # do setup work you want to do every time you enter the shell
  # Here are a few ideas that made sense to me:
  shellHook = ''
    if [[ ! -a "$PWD/py-yajl/setup.py" ]]; then
      git submodule update --init --recursive
    fi

    if [[ ! -a "$PWD/libc.so" ]]; then
      ${build_oil}
      ${test_oil}
    else
      echo "Dev build already exists. If you made changes, run:"
      echo "    'build/dev.sh clean' and "
      echo "    'build/dev.sh all' or 'build/dev.sh minimal'"
    fi

    ${cleanup_oil}
  '';
}

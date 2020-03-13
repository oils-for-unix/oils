# This file just defines non-oil/osh shells we need to build to run the tests.
{ pkgs ? import ./nixpkgs.nix }:

with pkgs; rec {
  pythonDeps = with python27Packages; [
    setuptools
    flake8
    pyannotate
    six
    typing
  ];
  oilPython = python27.withPackages (ps: with ps; pythonDeps);
  py-yajl = python27Packages.buildPythonPackage rec {
    pname = "oil-pyyajl";
    version = "unreleased";
    src = pkgs.fetchFromGitHub {
      owner = "oilshell";
      repo = "py-yajl";
      rev = "eb561e9aea6e88095d66abcc3990f2ee1f5339df";
      sha256 = "17hcgb7r7cy8r1pwbdh8di0nvykdswlqj73c85k6z8m0filj3hbh";
      fetchSubmodules = true;
    };
    nativeBuildInputs = [ pkgs.git ];
  };

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
  static_analysis =
    [ (python37.withPackages (ps: with ps; [ mypy ])) oilPython ];
  binary = [ re2c ];
  doctools = [ cmark ];
  c_deps = [ readline ];
  commands = [
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
  buildInputs = c_deps ++ binary ++ doctools ++ commands ++ doctools
    ++ [ py-yajl makeWrapper ] ++ static_analysis;
}

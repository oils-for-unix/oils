# Nix shell expression for the oil shell (formatted with nixfmt)
#   Note: run `nixfmt shell.nix` in nix-shell to reformat in-place
#
# By default fetch the most-recent 19.09 version of the stable NixOS release.
# This should be fine, but if it causes trouble it can be pinned to ensure
# everyone is running exactly the same versions.
{ pkgs ? import ./nix/nixpkgs.nix }:

with pkgs;
let
  shells = import ./nix/test_shells.nix { inherit pkgs; };
  deps = import ./nix/oil_deps.nix { inherit pkgs; };

  # Standard builder from Nixpkgs that we use to build oil
in pkgs.python27Packages.buildPythonPackage rec {

  pname = "oil";
  version = "undefined";
  allowSubstitutes = false;
  # Take the current folder
  src = ./.;

  # or take the git repo
  # src = builtins.fetchGit ./.;

  # or get it from a git commit
  # src = fetchFromGitHub {
  #   owner = "oilshell";
  #   repo = "oil";
  #   rev = "c40f53898db021bdb9dbd3fcbcfb11201fe92fe6";
  #   sha256 = "1jhczk0cr8v0h0vi3k2m9a61hgdaxlf1nrfbkz8ks5k7xw58mwss";
  #   fetchSubmodules = true;
  # };
  buildInputs = deps.buildInputs;
  nativeBuildInputs = [ deps.py-yajl ] ++ deps.binary ++ deps.commands
    ++ deps.static_analysis;
  propagatedBuildInputs = [ re2c deps.py-yajl deps.oilPython ];

  checkInputs = with shells;
    [ deps.py-yajl ] ++ [ test_bash test_dash test_mksh test_zsh ]
    ++ lib.optionals (stdenv.isLinux) [ shells.test_busybox ]
    ++ deps.static_analysis;
  doCheck = true;
  dontStrip = true;

  # Cannot build wheel otherwise (zip 1980 issue)
  SOURCE_DATE_EPOCH = 315532800;

  LOCALE_ARCHIVE = pkgs.lib.optionalString (buildPlatform.libc == "glibc")
    "${glibcLocales}/lib/locale/locale-archive";

  preBuild = ''
    build/dev.sh all
  '';

  # Patch shebangs so Nix can find all executables
  postPatch = ''
    patchShebangs asdl benchmarks build core doctools frontend native oil_lang spec test types
    substituteInPlace test/spec.sh --replace 'readonly REPO_ROOT=$(cd $(dirname $0)/..; pwd)' "REPO_ROOT=$out"
  '';

  dontWrapPythonPrograms = true;

  postInstall = ''
    mkdir -p $out/_devbuild/gen/ $out/_devbuild/help/
    install _devbuild/gen/*.marshal $out/_devbuild/gen/
    install _devbuild/help/* $out/_devbuild/help/
    install oil-version.txt $out/${deps.oilPython.sitePackages}/

    buildPythonPath "$out $propagatedBuildInputs"

    for executable in oil osh; do
      makeWrapper $out/bin/oil.py $out/bin/$executable \
        --add-flags $executable \
        --prefix PATH : "$program_PATH" \
        --prefix PYTHONPATH : "$program_PYTHONPATH" \
        --set _OVM_RESOURCE_ROOT "$out/${deps.oilPython.sitePackages}" \
        --set PYTHONNOUSERSITE true ${
          if glibcLocales != null then
            " --run \"export LOCALE_ARCHIVE='${glibcLocales}/lib/locale/locale-archive'\""
          else
            ""
        }
      substituteInPlace $out/bin/$executable --replace "${bash}/bin/bash" "${shells.bang_bash}/bin/bash"
    done
  '';

  checkPhase = ''
    ./test.sh
  '';

  prePatch = ''
    substituteInPlace ./doctools/cmark.py --replace "/usr/local/lib/libcmark.so" "${cmark}/lib/libcmark${stdenv.hostPlatform.extensions.sharedLibrary}"
  '';
}

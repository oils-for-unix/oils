# Nix expression for the oil shell
#
# By default fetch the latest version of the stable NixOS release
{ nixpkgs ? fetchTarball "channel:nixos-19.09"
}:

let
  # Import the package set.
  pkgs = import nixpkgs {};

  # Function for building oil
  oil =
    { stdenv
    , lib
    , fetchurl
    , fetchpatch
    , readline
    , python2
    , mypy
    , dash
    , mksh
    , zsh
    , time
    , re2c
  }:

    # Standard builder from Nixpkgs that we use to build oil
    stdenv.mkDerivation rec {
      pname = "oil";
      version = "0.7.pre5";

      # Take the current folder and remove .git
      src = lib.cleanSource ./.;

      # Patch shebangs so Nix can find all executables
      postPatch = ''
        patchShebangs build
      '';

      preInstall = ''
        mkdir -p $out/bin
      '';

      nativeBuildInputs = [ re2c ];
      buildInputs = [ readline ];
      configureFlags = [ "--with-readline" ];

      checkInputs = [
        dash
        mksh
        time
        zsh
        (python2.withPackages(ps: with ps; [ flake8 ]))
        mypy # This is the Python 3 version
      ];

      doCheck = true;

      # Stripping breaks the bundles by removing the zip file from the end.
      dontStrip = true;

      meta = {
        description = "A new unix shell";
        homepage = https://www.oilshell.org/;
        license = with lib.licenses; [
          psfl # Includes a portion of the python interpreter and standard library
          asl20 # Licence for Oil itself
        ];
      };

      passthru = {
        shellPath = "/bin/osh";
      };
    };

# Call the oil function and use as arguments the values in the `pkgs` set.
in pkgs.callPackage oil {}

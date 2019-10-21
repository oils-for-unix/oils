# Nix shell expression for the oil shell
#
# By default fetch the latest version of the stable NixOS release
{ nixpkgs ? fetchTarball "channel:nixos-19.09"
}:

let
  # Import the package set.
  pkgs = import nixpkgs {};

  # Function for building oil
  oil =
    { mkShell
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

    # Create a shell with packages we need.
    mkShell rec {

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

      doCheck = true; # Only exists so we can use checkInputs instead of nativeBuildInputs
    };

# Call the oil function and use as arguments the values in the `pkgs` set.
in pkgs.callPackage oil {}
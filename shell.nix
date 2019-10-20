let
  pkgs = import (builtins.fetchTarball {
    name = "nixos-unstable-2019-10-20";  # Descriptive name
    url = https://github.com/nixos/nixpkgs-channels/archive/1c40ee6fc44f7eb474c69ea070a43247a1a2c83c.tar.gz;
    sha256 = "0xvgx4zsz8jk125xriq7jfp59px8aa0c5idbk25ydh2ly7zmb2df";
  }) {};

in pkgs.oil.overrideAttrs(old: {
  buildInputs = old.buildInputs ++ [ pkgs.python2 ];
  patches = [];
  src = pkgs.lib.cleanSource ./.;
})

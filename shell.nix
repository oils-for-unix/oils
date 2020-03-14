# Nix shell expression for the oil shell (formatted with nixfmt)
#   Note: run `nixfmt shell.nix` in nix-shell to reformat in-place
#
# By default fetch the most-recent 19.09 version of the stable NixOS release.
# This should be fine, but if it causes trouble it can be pinned to ensure
# everyone is running exactly the same versions.
{ pkgs ? import ./nix/nixpkgs.nix }:

let
  shells = import ./nix/test_shells.nix { inherit pkgs; };
  drv = import ./default.nix { inherit pkgs; };
  deps = import ./nix/oil_deps.nix { inherit pkgs; };
in with pkgs;

# Create a shell with packages we need.
mkShell rec {
  # pull most deps from default.nix
  buildInputs = with shells; [ test_bash test_dash test_mksh test_zsh ] ++ lib.optionals (stdenv.isLinux) [ test_busybox ] ++ drv.buildInputs ++ [
    nixfmt # `nixfmt *.nix` to format in place
  ];

  # Note: Nix automatically adds identifiers declared here to the environment!
  _NIX_SHELL_LIBCMARK =
    "${cmark}/lib/libcmark${stdenv.hostPlatform.extensions.sharedLibrary}";

  # Need nix to relax before it'll link against a local file.
  NIX_ENFORCE_PURITY = 0;
  LANG = "en_US.UTF-8";

  # do setup work you want to do every time you enter the shell
  # Here are a few ideas that made sense to me:
  shellHook = ''
    # Have to prefix test bash; there'll be 3+ on path
    PATH="${shells.test_bash}/bin:$PATH"
    export _OVM_RESOURCE_ROOT="$PWD"
    ${if glibcLocales != null then
      "export LOCALE_ARCHIVE='${glibcLocales}/lib/locale/locale-archive'"
    else
      ""}
  '';
}

# This file just defines non-oil/osh shells we need to build to run the tests.
{ pkgs ? import ./nixpkgs.nix }:

rec {
  # bang_bash is patched to keep it from unsetting PS1/PS2 when the
  # shell isn't interactive. (Tests that fiddle with PS1/2 will break
  # without this.
  bang_bash = pkgs.bash.overrideAttrs (oldAttrs: rec {
    buildInputs = oldAttrs.buildInputs ++ [ pkgs.makeWrapper ];
    outputs = [ "out" ]; # don't need man/lib and such
    postPatch = ''
      substituteInPlace shell.c --replace "unbind_variable" "// unbind_variable"
    '';
  });

  # "with pkgs" brings pkgs.* into scope within the curly brace
  # using it for brevity here, but using both forms in this file
  # so that you can see them both in action.
  test_bash = pkgs.bash.overrideAttrs (oldAttrs:
    with pkgs; rec {
      # borrowed from https://github.com/NixOS/nixpkgs/blob/master/pkgs/shells/bash/4.4.nix
      # except to skip external readline in favor of built-in readline
      configureFlags =
        lib.optionals (stdenv.hostPlatform != stdenv.buildPlatform) [
          "bash_cv_job_control_missing=nomissing"
          "bash_cv_sys_named_pipes=nomissing"
          "bash_cv_getcwd_malloc=yes"
        ] ++ lib.optionals stdenv.hostPlatform.isCygwin [
          "--without-libintl-prefix"
          "--without-libiconv-prefix"
          "--enable-readline"
          "bash_cv_dev_stdin=present"
          "bash_cv_dev_fd=standard"
          "bash_cv_termcap_lib=libncurses"
        ] ++ lib.optionals (stdenv.hostPlatform.libc == "musl") [
          "--without-bash-malloc"
          "--disable-nls"
        ];
      outputs = [ "out" ];
    });

  test_busybox = pkgs.busybox-sandbox-shell.overrideAttrs (oldAttrs: rec {
    name = "busybox-1.31.1";
    src = pkgs.fetchurl {
      url = "https://busybox.net/downloads/${name}.tar.bz2";
      sha256 = "1659aabzp8w4hayr4z8kcpbk2z1q2wqhw7i1yb0l72b45ykl1yfh";
    };
  });

  test_dash = pkgs.dash.overrideAttrs (oldAttrs: rec {
    name = "dash-0.5.8";
    src = pkgs.fetchurl {
      url = "http://gondor.apana.org.au/~herbert/dash/files/${name}.tar.gz";
      sha256 = "03y6z8akj72swa6f42h2dhq3p09xasbi6xia70h2vc27fwikmny6";
    };
  });

  test_mksh = pkgs.mksh.overrideAttrs (oldAttrs: rec {
    version = "52";
    src = pkgs.fetchurl {
      urls = [
        "https://www.mirbsd.org/MirOS/dist/mir/mksh/mksh-R${version}.tgz"
        "http://pub.allbsd.org/MirOS/dist/mir/mksh/mksh-R${version}.tgz"
      ];
      sha256 = "13vnncwfx4zq3yi7llw3p6miw0px1bm5rrps3y1nlfn6sb6zbhj5";
    };
  });

  test_zsh = pkgs.zsh.overrideAttrs (oldAttrs: rec {
    version = "5.1.1";
    src = pkgs.fetchurl {
      url = "mirror://sourceforge/zsh/zsh-${version}.tar.xz";
      sha256 = "1v1xilz0fl9r9c7dr2lnn7bw6hfj0gbcz4wz1ybw1cvhahxlbsbl";
    };
  });
}

# TODO(akavel): also create default.nix for compatibility with "classic nix"
# TODO(akavel): merge back stuff from shell.nix - ideally into mkDerivation's shellHook attribute
# TODO(akavel): try using `nixfmt`?

{
  description = "A new Unix shell. Our upgrade path from bash to a better language and runtime.";

  inputs.nixpkgs-re2c-1-0-3 = {
    url = github:NixOS/nixpkgs/nixos-19.09;
    flake = false;  # see: https://nixos.wiki/wiki/Flakes#Flake_schema
  };

  inputs.nixpkgs-mypy-0-740 = {
    url = github:NixOS/nixpkgs/nixos-20.03;
    flake = false;  # see: https://nixos.wiki/wiki/Flakes#Flake_schema
  };

  outputs = { self, nixpkgs, nixpkgs-re2c-1-0-3, nixpkgs-mypy-0-740 }: {

    # defaultPackage.x86_64-linux = self.packages.x86_64-linux.oil;
    # defaultPackage.x86_64-linux = self.packages.x86_64-linux.oil-tarball;
    defaultPackage.x86_64-linux = self.packages.x86_64-linux.toil-run-cpp;

    # TODO(akavel): oil? or oil-cpp? or osh? or "all"? or...?
    packages.x86_64-linux.toil-run-cpp =
      with nixpkgs.legacyPackages.x86_64-linux;
      let
        selfpkgs = self.packages.x86_64-linux;
        re2c-1-0-3 = (import nixpkgs-re2c-1-0-3 { system = "x86_64-linux"; }).pkgs.re2c;
        mypy-0-730 = (import nixpkgs-mypy-0-740 { system = "x86_64-linux"; }).pkgs.mypy.overrideDerivation (old: {
          version = "0.730";
          src = python3Packages.fetchPypi {
            pname = "mypy";
            version = "0.730";
            sha256 = "0ygqviby0i4i3k2mlnr08f07dxvkh5ncl17m14bg4w07x128k9s2";
          };
        });
      in stdenv.mkDerivation {
        name = "oil"; # FIXME(akavel): correct or not?
        version = "dev";
        src = self;
        # FIXME(akavel): nativeBuildInputs? or buildInputs? always confuse them :(
        nativeBuildInputs = [
          git # TODO(akavel): try to make it unnecessary
          python2
          readline
          re2c-1-0-3
          mypy-0-730
          # FIXME(akavel): do we need separate mypy above with the line below?
          (python3.withPackages (ps: with ps; [ mypy-0-730 ]))
        ];
        patches = [
          ./nix-yajl.patch
          # TODO(akavel): according to current flakes docs, we could recover timestamp (via lastModifiedDate or lastModified) and hash (via rev),
          # see: https://github.com/NixOS/nix/blob/0df69d96e02ce4c9e17bd33333c5d78313341dd3/src/nix/flake.md#flake-format
          ./nix-no-git.patch
        ];
        postPatch = 
        # TODO(akavel): is the patchShebangs command below overeager?
        ''
          patchShebangs */*.{sh,py}
          patchShebangs mycpp/*/*.{sh,py}
        ''
        # Without this, `pushd py-yajl` fails in some scripts
        + ''
          ln -s ${selfpkgs.py-yajl.src} py-yajl
        ''
        # Equivalent to patched-out yajl() function in build/dev.sh
        + ''
          ln -s ${selfpkgs.py-yajl}/lib/python2.7/site-packages/yajl.so .
        ''
        # Disarm `test/cpp-unit.sh deps`, provide re2c via Nix instead
        + ''
          mkdir -p _deps
          ln -s ${re2c-1-0-3} _deps/re2c-1.0.3
        ''
        # Patch out mycpp-clone and mycpp-deps, provide mycpp via Nix instead
        # TODO(akavel): can we somehow make things smarter so that we don't have to do below block?
        # FIXME(akavel): also, shouldn't hardcode python3.8 here
        # FIXME(akavel): also, the mypy below should probably be mypy-0-730 !!!!!
        + ''
          mkdir -p _clone
          ln -s ${mypy}/lib/python3.8/site-packages _clone/mypy
          sed -i \
            -e '/^mycpp-clone /d' \
            -e '/^mycpp-deps /d' \
            services/toil-worker.sh
        ''
        # 'activate' is not necessary, because Nix effectively replaces virtualenv.
        # TODO(akavel): can we make below PYTHONPATH tweaks unnecessary?
        + ''
          grep -rl '_tmp/mycpp-venv/bin/activate' {build,mycpp}/*.sh |
            xargs -n1 sed -i \
              -e 's|source _tmp/mycpp-venv/bin/activate|true "PATCHED OUT _tmp/mycpp-venv/bin/activate/"|' \
              -e 's|\bPYTHONPATH=$MYPY_REPO |PYTHONPATH=$_NIXPYTHONPATH |'
          export _NIXPYTHONPATH=$PYTHONPATH
        ''
        # NOTE(akavel): https://mypy.readthedocs.io/en/latest/running_mypy.html#mapping-file-paths-to-modules
        # Otherwise, mypy gets confused w.r.t. module paths. (Why is this file even here?)
        + ''
          rm __init__.py
        '';
        buildPhase = ''
          runHook preBuild

          services/toil-worker.sh run-cpp

          runHook postBuild
        '';
        # FIXME(akavel): what we do in installPhase?
        installPhase = ''
          mkdir -p $out
          tar c -C _tmp toil | tar x -C $out/
        '';
      };

    packages.x86_64-linux.py-yajl =
      with nixpkgs.legacyPackages.x86_64-linux;
      let
        selfpkgs = self.packages.x86_64-linux;
      in pkgs.python27Packages.buildPythonPackage {
        pname = "py-yajl";
        # pname = "py-yajl-oil";
        version = "dev";
        src = pkgs.fetchFromGitHub {
          # FIXME(akavel): source package is not os-dependent; where to put it in flake?
          owner = "oilshell";
          repo = "py-yajl";
          rev = "eb561e9aea6e88095d66abcc3990f2ee1f5339df";
          sha256 = "09piyj7rmhgpqm84ynhdkywmpfshckyiphwhrs6k5gnbm3m356p3";
        };
        doCheck = false; # skip tests
        nativeBuildInputs = [ pkgs.git ];
        preBuild = ''
          rmdir yajl
          ln -s ${selfpkgs.yajl.src} yajl
        '';
      };

    packages.x86_64-linux.yajl =
      with nixpkgs.legacyPackages.x86_64-linux;
      {
        src = pkgs.fetchFromGitHub {
          # FIXME(akavel): source package is not os-dependent; where to put it in flake?
          owner = "lloyd";
          repo = "yajl";
          rev = "5e3a7856e643b4d6410ddc3f84bc2f38174f2872";
          sha256 = "1s4w2938s12ximaqc8v3k3knmxpi1l9j1gb5q1n3cwamzhn00jfh";
        };
      };
  };
}

# for now I'm just pinning this to the nixos-19.09 channel
# it's a little more conservative than using unstable
# can go further and pin to a *specific* nixpkgs commit like:
# https://github.com/NixOS/nixpkgs-channels/archive/e6b8eb0280be5b271a52c606e2365cb96b7bd9f1.tar.gz
import (fetchTarball "channel:nixos-19.09") { }

# Can get even *more* conservative by asserting a hash:
# import (builtins.fetchGit {
# 	name = "nixpkgs-unstable-2020-02-17";
# 	url = https://github.com/nixos/nixpkgs-channels/;
# 	ref = "refs/heads/nixpkgs-unstable";
# 	rev = "f77e057cda60a3f96a4010a698ff3be311bf18c6";
# }) { }

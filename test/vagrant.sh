#!/bin/bash
#
# Usage:
#   ./vagrant.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO:
# - FreeBSD - fix
# - OpenBSD - no official image

# - 32-bit https://app.vagrantup.com/puppetlabs/boxes/ubuntu-16.04-32-puppet
# Or a really old one:
# - https://app.vagrantup.com/hashicorp/boxes/precise32


# Hm lots of Ruby dependencies.
install() {
  sudo apt install vagrant
  sudo apt install virtualbox
}

# Downloads the image, run it, set up SSH stuff (keys, etc.).
archlinux() {
  # Hm does this only happen once per dir?
  vagrant init archlinux/archlinux
  vagrant up
}

# vagrant ssh to log in.  ~/git/oil is mounted to /vagrant.  User is 'vagrant'.

# sudo pacman -S gcc make
# Then untar ~/src/oil-$VERSION.tar.


# centos/7
# sudo yum install gcc make

# (NOTES: yum figures out the fastest mirror)


# $ make
# build/compile.sh build-opt _build/oil/ovm _build/oil/module_init.c _build/oil/main_name.c _build/oil/c-module-srcs.txt
# ~/src/oil-0.1.alpha1/Python-2.7.13 ~/src/oil-0.1.alpha1
# Modules/posixmodule.c:3914:21: fatal error: stropts.h: No such file or directory
# #include <stropts.h>
#                     ^
# compilation terminated.
# Modules/fcntlmodule.c:15:21: fatal error: stropts.h: No such file or directory
#  #include <stropts.h>

"$@"

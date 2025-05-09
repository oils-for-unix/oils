#!/usr/bin/env bash
#
# Testing batch files

set -o nounset
set -o pipefail
set -o errexit

# several hundred megs

# weird error:
# it looks like wine32 is missing, you should install it.
# multiarch needs to be enabled first.  as root, please
# execute "dpkg --add-architecture i386 && apt-get update &&
# apt-get install wine32:i386"

BAD-install-wine() {
  #sudo apt-get update
  sudo apt-get install wine wine64 #winetricks
}

# OK let's fix it.
# This is hundreds of megabytes on top

BAD-install-wine-2() {
  dpkg --add-architecture i386 
  apt-get update 
  apt-get install wine32:i386
}


readonly DIR=_tmp/wine

batch() {
  mkdir -p $DIR
  echo 'echo hello world' > $DIR/hi.bat

  echo "
@echo off  
:: echo off is global

:: call is required
CALL $DIR/hi.bat

dir $DIR | find .bat

CALL $DIR/hi.bat

" > $DIR/invoke.bat

  #echo 'dir' > $DIR/test.bat
  #echo 'dir | find ".bat"' > $DIR/test.bat

  # woah this brings up a GUI?
  wine cmd /c $DIR/invoke.bat
}

# doesn't work?

# $ wine cmd /c echo "hello world"
# wine: could not load kernel32.dll, status c0000135


# OK these instructions work:
#
# https://gitlab.winehq.org/wine/wine/-/wikis/Debian-Ubuntu

wine-key() {
  wget -O - https://dl.winehq.org/wine-builds/winehq.key |
    sudo gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key -
}

add-wine-repo() {
  # for Debian 12
  sudo wget -NP /etc/apt/sources.list.d/ \
    https://dl.winehq.org/wine-builds/debian/dists/bookworm/winehq-bookworm.sources
}

install() {
  sudo apt install --install-recommends winehq-stable
}

"$@"

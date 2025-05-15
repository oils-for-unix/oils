#!/usr/bin/env bash
#
# Test bash, python3, C and C++ under Wine!
#
# Notes:
#   python3 is called python.exe on Windows
#
# Other things to try:

# - python3
#   - test out asyncio on Windows! 
#   - especially process creation
#   - a test framework for stdin/stdout/stderr would be nice 
#     - can sh_spec.py work with non-shell scripts?
#
# - git
#   - can we clone our repo?  commit?
#
# And then do this all inside QEMU - it seems more automated than VirtualBox
#
# - do automated installation of everything?

readonly DIR=_tmp/win32

my-curl() {
  curl --location --continue-at - \
    --remote-name --output-dir $DIR "$@"
}

download() {
  mkdir -p $DIR

  my-curl 'https://www.python.org/ftp/python/3.13.3/python-3.13.3-amd64.exe'

  my-curl \
    'https://github.com/git-for-windows/git/releases/download/v2.49.0.windows.1/Git-2.49.0-64-bit.exe'

  my-curl \
    'https://github.com/jmeubank/tdm-gcc/releases/download/v10.3.0-tdm64-2/tdm64-gcc-10.3.0-2.exe'
}

find-python() {
  find ~/.wine/drive_c/|grep python.exe
}

test-python3() {
  # takes 326 ms
  time wine \
    ~/.wine/drive_c/users/andy/AppData/Local/Programs/Python/Python313/python.exe \
    -c 'print("hi")'
}

readonly BASH=~/'.wine/drive_c/Program Files/Git/bin/bash.exe'
readonly GIT_BASH=~/'.wine/drive_c/Program Files/Git/git-bash.exe'

test-bash() {
  # 378 ms
  # works, but getting a bunch of warnings

  # Hm this respects $PATH, finds python
  time wine "$BASH" -c 'echo "hi from bash"; python.exe -c "print(\"hi from python3\")"'

  #time wine "$GIT_BASH" -c 'echo hi'
}

test-gcc() {
  echo '
#include <iostream>
int main() {
    std::cout << "Hello from C++ in Wine!" << std::endl;
    return 0;
}' > $DIR/hello.cpp

  wine cmd /c "g++ $DIR/hello.cpp -o $DIR/hello.exe"

  wine $DIR/hello.exe

}

build-create-process() {
  wine cmd /c "g++ win32/create-process.c -o $DIR/create-process.exe"
}

run-create-process() {
  wine $DIR/create-process.exe
}

test-powershell() {
  # this doesn't work?  It's a stub?
  wine cmd /c 'powershell.exe -Command "Write-Host hello from powershell"'
}

test-pipelines() {
  #wine cmd /c 'dir win32/demo_asyncio.py'

  echo 'UNIX SUBPROCESS'
  win32/demo_subprocess.py
  echo

  echo 'UNIX ASYNCIO'
  win32/demo_asyncio.py
  echo

  echo 'WIN32 SUBPROCESS'
  wine cmd /c 'python.exe win32/demo_subprocess.py'
  echo

  echo 'WIN32 ASYNCIO'
  wine cmd /c 'python.exe win32/demo_asyncio.py'
}

test-mycpp-hello() {
  #wine cmd /c 'cd _tmp/hello-tar-test/hello-0.29.0; bash.exe -c "echo bash"'

  time wine "$BASH" -c '
echo "hi from bash"

set -o errexit

# cross-shell tracing works!
set -x

# mkdir works!
mkdir -p _tmp/hi-from-wine

cd _tmp/hello-tar-test/hello-0.29.0
pwd
ls -l 

set +e
mkdir -p _bin/cxx-opt-sh/mycpp _build/obj/cxx-opt-sh/_gen/bin _build/obj/cxx-opt-sh/mycpp
echo mkdir=$?

if false; then
for dir in _bin/cxx-opt-sh/mycpp _build/obj/cxx-opt-sh/_gen/bin _build/obj/cxx-opt-sh/mycpp; do
  echo "   ---"
  echo "   $dir"
  ls -l $dir
done
fi

export SHELLOPTS

set +o errexit
_build/oils.sh
echo status=$?
'
}

test-mkdir() {
  #wine cmd /c 'cd _tmp/hello-tar-test/hello-0.29.0; bash.exe -c "echo bash"'

  chmod +x _tmp/hello-tar-test/hello-0.29.0/_build/mkdir-test.sh

  time wine "$BASH" -c '
echo "hi from bash"

set -o errexit

# cross-shell tracing works!
set -x

# mkdir works!
mkdir -p _tmp/hi-from-wine

cd _tmp/hello-tar-test/hello-0.29.0
pwd
ls -l 

set +e
mkdir -p _bin/cxx-opt-sh/mycpp _build/obj/cxx-opt-sh/_gen/bin _build/obj/cxx-opt-sh/mycpp
echo mkdir=$?

_build/mkdir-test.sh
'
}

"$@"

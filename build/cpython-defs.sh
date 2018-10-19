#!/bin/bash
#
# Usage:
#   ./cpython-defs.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO:
# Write to a separate file like _build/pydefs/intobject.include
# #ifdef OVM_MAIN
# #include "intobject.include"
# #else
# ...
# #end
#
# Should those files be checked in an edited by hand?  Or join them somehow
# with oil-symbols.txt?
# I think this is hard because of METHODS.
# Maybe you should have a config file that controls it.  It takes a .include
# file and then whitelist/blacklist, and then generates a new one.
# could put it in build/pydefs-config.txt
#
# And then reprint the PyMethoDef without docstrings?  It shouldn't be that
# hard to parse.  You can almost do it with a regex, since commas don't appear
# in the string.

extract-defs() {
  local path_prefix=$1  # to strip
  local edit_list=_tmp/cpython-defs/edit-list.txt

  # NOTE: PyMemberDef is also interesting, but we don't need it for the build.
  gawk -v path_prefix_length=${#path_prefix} -v edit_list=$edit_list '
  /static PyMethodDef/ {
    if (printing != 0) {
      printf("%s:%d Expected not to be printing\n", FILENAME, FNR);
      exit 1;
    }
    printing = 1;
    start_line_num = FNR;

    rel_path = substr(FILENAME, path_prefix_length + 1);
    if (!found[FILENAME]) {
      # This special line seems to survive the preprocessor?
      printf("\n");
      printf("FILE %s\n", rel_path);
      printf("\n");

      printf("Filtering %s\n", FILENAME) > "/dev/stderr";
      found[FILENAME] = 1  # count number of files that have matches
    }
  }

  {
    if (printing) {
      print
    }
  }

  /^[:space:]*\}/ {
    if (printing) {
      # Print the edit list for #ifdef #endif.
      end_line_num = FNR;
      printf("%s %d %d\n", rel_path, start_line_num, end_line_num) > edit_list;
      printing = 0;
    }
  }

  END {
    for (name in found) {
      num_found++;
    }
    printf("extract-defs.awk: Found definitions in %d out of %d files\n",
           num_found, ARGC) > "/dev/stderr";
  }
  ' "$@"
}

source build/common.sh  # $PY27

# TODO: Use PREPROC_FLAGS from build/compile.sh.
preprocess() {
  # What about stuff in pyconfig.h?
  gcc -I $PY27 -E -D OVM_MAIN -
}

readonly TARBALL_ROOT=$(echo _tmp/oil-tar-test/oil-*)

extract-all-defs() {
  echo '#include "pyconfig.h"'
  # 52 different instances.  Sometimes multiple ones per file.
  find "$TARBALL_ROOT" -name '*.c' | xargs -- $0 extract-defs "$TARBALL_ROOT/"
}

cpython-defs() {
  PYTHONPATH=. build/cpython_defs.py "$@"
}

py-method-defs() {
  local tmp=_tmp/cpython-defs
  mkdir -p $tmp
  extract-all-defs > $tmp/extracted.txt
  cat $tmp/extracted.txt | preprocess > $tmp/preprocessed.txt

  #head -n 30 $tmp
  cat $tmp/preprocessed.txt | cpython-defs filter $tmp

  wc -l $tmp/*/*.defs
  wc -l $tmp/*.txt

  # syntax check
  #cc _tmp/filtered.c
}

"$@"

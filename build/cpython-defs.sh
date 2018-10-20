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
  shift

  local edit_list=_tmp/cpython-defs/edit-list.txt

  # NOTE: PyMemberDef is also interesting, but we don't need it for the build.
  gawk -v path_prefix_length=${#path_prefix} -v edit_list=$edit_list '
  /static PyMethodDef/ {
    if (printing != 0) {
      printf("%s:%d Expected not to be printing\n", FILENAME, FNR) > "/dev/stderr";
      exit 1;
    }
    # NOTE: We had to adjust stringobject.c and _weakref.c so that the name is
    # on one line!  Not a big deal.
    if (match($0, /static PyMethodDef ([a-zA-Z0-9_]+)\[\]/, m)) {
      def_name = m[1];
    } else {
      printf("%s:%d Could not parse declaration name\n",
             FILENAME, FNR) > "/dev/stderr";
      exit 1;
    }
    printing = 1;
    line_begin = FNR;

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
      line_end = FNR;
      printf("%s %s %d %d\n", rel_path, def_name, line_begin, line_end) > edit_list;
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

readonly BASE_DIR=_tmp/cpython-defs

py-method-defs() {
  local tmp=$BASE_DIR
  mkdir -p $tmp
  extract-all-defs > $tmp/extracted.txt
  cat $tmp/extracted.txt | preprocess > $tmp/preprocessed.txt

  local out_dir=build/oil-defs
  mkdir -p $out_dir

  #head -n 30 $tmp
  cat $tmp/preprocessed.txt | cpython-defs filter $out_dir

  wc -l $tmp/*/*.defs
  wc -l $tmp/*.txt

  # syntax check
  #cc _tmp/filtered.c
}

methods-tsv() {
  local out=_tmp/metrics/native-code/cpython-methods.tsv
  cat $BASE_DIR/preprocessed.txt | cpython-defs tsv | tee $out
}

edit-file() {
  local rel_path=$1
  local def_name=$2
  local line_begin=$3
  local line_end=$4

  local def_path="${rel_path}/${def_name}.def"

  local tmp=_tmp/buf.txt

  # DESTRUCTIVE
  mv $rel_path $tmp

  gawk -v def_path=$def_path -v line_begin=$line_begin -v line_end=$line_end '
  NR == line_begin {
    print("#ifdef OVM_MAIN")
    printf("#include \"%s\"\n", def_path)
    print("#else")
    print  # print the PyMethodDef line {
    next
  }
  NR == line_end {
    print  # print the }
    print("#endif"); 
    next
  }
  # All other lines just get printed
  {
    print
  }
  ' $tmp > $rel_path

  echo "Wrote $rel_path"
}

edit-all() {
  # Reversed so that edits to the same file work!  We are always inserting
  # lines.
  tac _tmp/cpython-defs/edit-list.txt | xargs -n 4 -- $0 edit-file
}

"$@"

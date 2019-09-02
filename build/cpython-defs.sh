#!/bin/bash
#
# Usage:
#   ./cpython-defs.sh <function name>
#
# Example:
#
#   # make clean tree of .c files
#   devtools/release.sh quick-oil-tarball
#   build/test.sh oil-tar  # can Ctrl-C this
#
#   build/cpython-defs.sh oil-py-names  # extract names
#   build/cpython-defs.sh filter-methods
#
# NOTE: 'build/compile.sh make-tar' is complex, so it's easier to just extract
# the tarball, even though it leads to a weird dependency.

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # R_PATH

readonly BASE_DIR=_tmp/cpython-defs

# Could be published in metrics?
readonly PY_NAMES=_tmp/oil-py-names.txt

# Print the .py files in the tarball in their original locations.  For slimming
# down the build.  Similar to build/metrics.sh linecounts-pydeps.
# Hm that doesn't seem to duplicate posixpath while this does?
oil-py-deps() {
  cat _build/oil/opy-app-deps.txt | awk ' $1 ~ /\.py$/ { print $1 }'
}

oil-py-names() {
  time oil-py-deps | xargs bin/opyc lex-names | sort | uniq > $PY_NAMES

  wc -l $PY_NAMES
}

# NOTE: We can replace os with posix.  Will save 700 lines of code, 25K + 25K.
# os.getenv() is a trivial wrapper around os.environ.get().  It gets
# initialized in posixmodule.c.
os-module-deps() {
  #oil-py-deps | xargs egrep --no-filename -o '\bos\.[a-z]+' */*.py | sort | uniq -c |sort -n
  oil-py-deps | xargs egrep -l '\bos\.'
}

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

extract-methods() {
  local path_prefix=$1  # to strip
  shift

  local edit_list=$BASE_DIR/method-edit-list.txt

  # NOTE: PyMemberDef is also interesting, but we don't need it for the build.
  gawk -v path_prefix_length=${#path_prefix} -v edit_list=$edit_list '
  /static.*PyMethodDef/ {
    if (printing != 0) {
      printf("%s:%d Expected not to be printing\n", FILENAME, FNR) > "/dev/stderr";
      exit 1;
    }
    # NOTE: We had to adjust stringobject.c and _weakref.c so that the name is
    # on one line!  Not a big deal.
    if (match($0, /static.*PyMethodDef ([a-zA-Z0-9_]+)\[\]/, m)) {
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

  printing { print }

  # Looking for closing brace (with leading space)

  /^[:space:]*\}/ && printing {
    # Print the edit list for #ifdef #endif.
    line_end = FNR;
    printf("%s %s %d %d\n", rel_path, def_name, line_begin, line_end) > edit_list;
    printing = 0;
  }

  END {
    for (name in found) {
      num_found++;
    }
    printf("extract-methods.awk: Found definitions in %d out of %d files\n",
           num_found, ARGC) > "/dev/stderr";
  }
  ' "$@"
}

source build/common.sh  # $PY27

preprocess() {
  # TODO: Use PREPROC_FLAGS from build/compile.sh.
  # - What about stuff in pyconfig.h?
  # - Hack to define WTERMSIG!  We really need to include <sys/wait.h>, but
  # that causes parse errors in cpython_defs.py.  Really we should get rid of
  # this whole hack!
  # - WIFSTOPPED is another likely thing...
  gcc -I $PY27 -E -D OVM_MAIN -D WTERMSIG -
}

readonly TARBALL_ROOT=$(echo _tmp/oil-tar-test/oil-*)

extract-all-methods() {
  echo '#include "pyconfig.h"'
  # 52 different instances.  Sometimes multiple ones per file.
  find "$TARBALL_ROOT" -type f -a -name '*.c' \
    | xargs -- $0 extract-methods "$TARBALL_ROOT/"
}

cpython-defs() {
  PYTHONPATH=. build/cpython_defs.py "$@"
}

filter-methods() {
  local tmp=$BASE_DIR
  mkdir -p $tmp

  extract-all-methods > $tmp/extracted.txt
  cat $tmp/extracted.txt | preprocess > $tmp/preprocessed.txt

  local out_dir=build/oil-defs
  mkdir -p $out_dir

  #head -n 30 $tmp
  cat $tmp/preprocessed.txt | cpython-defs filter $PY_NAMES $out_dir

  echo
  find $out_dir -name '*.def' | xargs wc -l | sort -n

  echo
  wc -l $tmp/*.txt

  # syntax check
  #cc _tmp/filtered.c
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
  #tac $BASE_DIR/method-edit-list.txt | xargs -n 4 -- $0 edit-file

  # One-off editing
	grep typeobject.c $BASE_DIR/method-edit-list.txt \
    | tac | xargs -n 4 -- $0 edit-file

}

extract-types() {
  local path_prefix=$1  # to strip
  shift

  local edit_list=$BASE_DIR/type-edit-list.txt

  # NOTE: PyMemberDef is also interesting, but we don't need it for the build.
  gawk -v path_prefix_length=${#path_prefix} -v edit_list=$edit_list '
  function maybe_print_file_header() {
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

  /PyTypeObject.*=.*\{.*\}/ {
    if (printing != 0) {
      printf("%s:%d Expected not to be printing\n", FILENAME, FNR) > "/dev/stderr";
      exit 1;
    }
    // Found it all on one line
    print
    num_one_line_types++;
    next
  }

  /PyTypeObject.*=.*\{/ {
    if (printing != 0) {
      printf("%s:%d Expected not to be printing\n", FILENAME, FNR) > "/dev/stderr";
      exit 1;
    }
    printing = 1;
    line_begin = FNR;

    maybe_print_file_header()
    num_types++;
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
    printf("extract-types.awk: Found %d definitions in %d files (of %d files)\n",
           num_types, num_found, ARGC) > "/dev/stderr";
    printf("extract-types.awk: Also found %d types on one line\n",
           num_one_line_types) > "/dev/stderr";
  }
  ' "$@"
}

extract-all-types() {
  find "$TARBALL_ROOT" -type f -a -name '*.c' \
    | xargs -- $0 extract-types "$TARBALL_ROOT/"
}

#
# Analysis
#

readonly METRICS_DIR=_tmp/metrics/cpython-defs

# Show current Oil definitions literally.
show-oil() {
  find build/oil-defs -name '*.def' | xargs cat | less
}

# Show in a contenses format.
methods-audit() {
  mkdir -p $METRICS_DIR
  cat $BASE_DIR/preprocessed.txt | cpython-defs audit $PY_NAMES \
    | tee _tmp/methods.txt

  wc -l _tmp/methods.txt
}

methods-tsv() {
  mkdir -p $METRICS_DIR
  local out=$METRICS_DIR/methods.tsv
  cat $BASE_DIR/preprocessed.txt | cpython-defs tsv $PY_NAMES | tee $out
}

_report() {
  R_LIBS_USER=$R_PATH metrics/cpython-defs.R "$@"
}

report() {
  _report metrics $METRICS_DIR
}

run-for-release() {
  methods-tsv
  report | tee $METRICS_DIR/overview.txt
}

unfiltered() {
  cpython-defs filtered | sort > _tmp/left.txt
  awk '{print $1}' $BASE_DIR/edit-list.txt \
    | egrep -o '[^/]+$' \
    | sort | uniq > _tmp/right.txt
  diff -u _tmp/{left,right}.txt
}


"$@"

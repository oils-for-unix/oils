/*
 * Python interface to libc functions.
 */

// - Enable GNU extensions in fnmatch.h for extended glob.
// - It's also apparently needed for wchar.h in combination with Python.
//   https://github.com/python-pillow/Pillow/issues/1850
//   - It's currently hard-coded in pyconfig.h.
#define _GNU_SOURCE 1

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // printf
#include <limits.h>
#include <wchar.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <locale.h>
#include <fnmatch.h>
#include <glob.h>
#include <regex.h>

#include <Python.h>

// Log messages to stderr.
static void debug(const char* fmt, ...) {
#ifdef LIBC_VERBOSE
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
#endif
}

static PyObject *
func_realpath(PyObject *self, PyObject *args) {
  const char *symlink;

  if (!PyArg_ParseTuple(args, "s", &symlink)) {
    return NULL;
  }
  char target[PATH_MAX + 1];
  char *status = realpath(symlink, target);

  if (status == NULL) {
    debug("error from realpath()");
    Py_RETURN_NONE;
  }

  return PyString_FromString(target);
}

static PyObject *
func_fnmatch(PyObject *self, PyObject *args) {
  const char *pattern;
  const char *str;

  if (!PyArg_ParseTuple(args, "ss", &pattern, &str)) {
    return NULL;
  }

  // NOTE: Testing for __GLIBC__ is the version detection anti-pattern.  We
  // should really use feature detection in our configure script.  But I plan
  // to get rid of the dependency on FNM_EXTMATCH because it doesn't work on
  // musl libc (or OS X).  Instead we should compile extended globs to extended
  // regex syntax.
#ifdef __GLIBC__
  int flags = FNM_EXTMATCH;
#else
  debug("Warning: FNM_EXTMATCH is not defined");
  int flags = 0;
#endif

  const char *old_locale = setlocale(LC_CTYPE, NULL);
  if (setlocale(LC_CTYPE, "") == NULL) {
	  PyErr_SetString(PyExc_SystemError, "Invalid locale for LC_CTYPE");
	  return NULL;
  }

  int ret = fnmatch(pattern, str, flags);

  setlocale(LC_CTYPE, old_locale);

  switch (ret) {
  case 0:
    debug("matched: %s", str);
    return PyLong_FromLong(1);
    break;
  case FNM_NOMATCH:
    debug("no match: %s", str);
    return PyLong_FromLong(0);
    break;
  default:
    debug("other error: %s", str);
    return PyLong_FromLong(-1);
    break;
  }
}

// error callback to glob()
//
// Disabled because of spurious errors.  For example, sed -i s/.*// (without
// quotes) is OK, but it would be treated as a glob, and prints an error if the
// directory 's' doesn't exist.
//
// Bash does its own globbing -- it doesn't use libc.  Likewise, I think dash
// and mksh do their own globbing.

int globerr(const char *path, int eerrno) {
  fprintf(stderr, "globerr: %s: %s\n", path, strerror(eerrno));
  return 0;  // let glob() keep going
}

static PyObject *
func_glob(PyObject *self, PyObject *args) {
  const char* pattern;
  if (!PyArg_ParseTuple(args, "s", &pattern)) {
    return NULL;
  }

  glob_t results;
  // Hm, it's weird that the first one can't be called with GLOB_APPEND.  You
  // get a segfault.
  int flags = 0;
  // int flags = GLOB_APPEND;
  //flags |= GLOB_NOMAGIC;
  int ret = glob(pattern, flags, NULL, &results);

  const char *err_str = NULL;
  switch (ret) {
  case 0:  // no error
    break;
  case GLOB_ABORTED:
    err_str = "read error";
    break;
  case GLOB_NOMATCH:
    // No error, because not matching isn't necessarily a problem.
    // NOTE: This can be turned on to log overaggressive calls to glob().
    //err_str = "nothing matched";
    break;
  case GLOB_NOSPACE:
    err_str = "no dynamic memory";
    break;
  default:
    err_str = "unknown problem";
    break;
  }
  if (err_str) {
    fprintf(stderr, "func_glob: %s: %s\n", pattern, err_str);
  }

  // http://stackoverflow.com/questions/3512414/does-this-pylist-appendlist-py-buildvalue-leak
  size_t n = results.gl_pathc;
  PyObject* matches = PyList_New(n);

  // Print array of results
  size_t i;
  for (i = 0; i < n; i++) {
    //printf("%s\n", results.gl_pathv[i]);
    PyObject* m = Py_BuildValue("s", results.gl_pathv[i]);
    PyList_SetItem(matches, i, m);
  }
  globfree(&results);

  return matches;
}

static PyObject *
func_regex_parse(PyObject *self, PyObject *args) {
  const char* pattern;
  if (!PyArg_ParseTuple(args, "s", &pattern)) {
    return NULL;
  }
  regex_t pat;
  // This is an extended regular expression rather than a basic one, i.e. we
  // use 'a*' instaed of 'a\*'.
  int ret = regcomp(&pat, pattern, REG_EXTENDED);
  regfree(&pat);

  // Copied from man page

  const char *err_str = NULL;
  switch (ret) {
  case 0:  // success
    break;

  case REG_BADBR:
    err_str = "Invalid use of back reference operator.";
    break;

  case REG_BADPAT:
    err_str = "Invalid use of pattern operators such as group or list.";
    break;

  case REG_BADRPT:
    err_str = "Invalid use of repetition operators such as using '*' as the first character.";
    break;

  case REG_EBRACE:
    err_str = "Un-matched brace interval operators.";
    break;

  case REG_EBRACK:
    err_str = "Un-matched bracket list operators.";
    break;

  case REG_ECOLLATE:
    err_str = "Invalid collating element.";
    break;

  case REG_ECTYPE:
    err_str = "Unknown character class name.";
    break;

  case REG_EESCAPE:
    err_str = "Trailing backslash.";
    break;

  case REG_EPAREN:
    err_str = "Un-matched parenthesis group operators.";
    break;

  case REG_ERANGE:
    err_str = "Invalid use of the range operator, e.g., the ending point of the range occurs prior to the starting point.";
    break;

  case REG_ESPACE:
    err_str = "The regex routines ran out of memory.";
    break;

  case REG_ESUBREG:
    err_str = "Invalid back reference to a subexpression.";
    break;

    /* NOTE: These are not defined by musl libc on Alpine.
     * TODO: If we can construct test cases for these, add them back.
     * */
#if 0
  case REG_EEND:
    err_str = "Nonspecific error.  This is not defined by POSIX.2.";
    break;
  case REG_ESIZE:
    err_str = "Compiled regular expression requires a pattern buffer larger than 64Kb.  This is not defined by POSIX.2.";
    break;
#endif

  default:
    /* TODO: Add the integer to error message */
    err_str = "Unknown error compiling regex";
  }

  if (err_str) {
    // When the regex contains a variable, it can't be checked at compile-time.
    PyErr_SetString(PyExc_RuntimeError, err_str);
    return NULL;
  } else {
    Py_RETURN_TRUE;
  }
}

static PyObject *
func_regex_match(PyObject *self, PyObject *args) {
  const char* pattern;
  const char* str;
  if (!PyArg_ParseTuple(args, "ss", &pattern, &str)) {
    return NULL;
  }

  regex_t pat;
  if (regcomp(&pat, pattern, REG_EXTENDED) != 0) {
    // When the regex contains a variable, it can't be checked at compile-time.
    PyErr_SetString(PyExc_RuntimeError, "Invalid regex syntax (func_regex_match)");
    return NULL;
  }

  int outlen = pat.re_nsub + 1;
  PyObject *ret = PyList_New(outlen);

  if (ret == NULL) {
    regfree(&pat);
    return NULL;
  }

  int match;
  regmatch_t *pmatch = (regmatch_t*) malloc(sizeof(regmatch_t) * outlen);
  if (match = (regexec(&pat, str, outlen, pmatch, 0) == 0)) {
    int i;
    for (i = 0; i < outlen; i++) {
      int len = pmatch[i].rm_eo - pmatch[i].rm_so;
      PyObject *v = PyString_FromStringAndSize(str + pmatch[i].rm_so, len);
      PyList_SetItem(ret, i, v);
    }
  }

  free(pmatch);
  regfree(&pat);

  if (!match) {
    Py_RETURN_NONE;
  }

  return ret;
}

// For ${//}, the number of groups is always 1, so we want 2 match position
// results -- the whole regex (which we ignore), and then first group.
//
// For [[ =~ ]], do we need to count how many matches the user gave?

#define NMATCH 2

static PyObject *
func_regex_first_group_match(PyObject *self, PyObject *args) {
  const char* pattern;
  const char* str;
  int pos;
  if (!PyArg_ParseTuple(args, "ssi", &pattern, &str, &pos)) {
    return NULL;
  }

  regex_t pat;
  regmatch_t m[NMATCH];

  const char *old_locale = setlocale(LC_CTYPE, NULL);

  if (setlocale(LC_CTYPE, "") == NULL) {
	  PyErr_SetString(PyExc_SystemError, "Invalid locale for LC_CTYPE");
	  return NULL;
  }

  // Could have been checked by regex_parse for [[ =~ ]], but not for glob
  // patterns like ${foo/x*/y}.

  if (regcomp(&pat, pattern, REG_EXTENDED) != 0) {
    PyErr_SetString(PyExc_RuntimeError,
                    "Invalid regex syntax (func_regex_first_group_match)");
    return NULL;
  }

  debug("first_group_match pat %s str %s pos %d", pattern, str, pos);

  // Match at offset 'pos'
  int result = regexec(&pat, str + pos, NMATCH, m, 0 /*flags*/);
  regfree(&pat);

  setlocale(LC_CTYPE, old_locale);

  if (result != 0) {
    Py_RETURN_NONE;  // no match
  }

  // Assume there is a match
  regoff_t start = m[1].rm_so;
  regoff_t end = m[1].rm_eo;
  return Py_BuildValue("(i,i)", pos + start, pos + end);
}

// We do this in C so we can remove '%f' % 0.1 from the CPython build.  That
// involves dtoa.c and pystrod.c, which are thousands of lines of code.
static PyObject *
func_print_time(PyObject *self, PyObject *args) {
  double real, user, sys;
  if (!PyArg_ParseTuple(args, "ddd", &real, &user, &sys)) {
    return NULL;
  }
  fprintf(stderr, "real\t%.3f\n", real);
  fprintf(stderr, "user\t%.3f\n",  user);
  fprintf(stderr, "sys\t%.3f\n", sys);
  Py_RETURN_NONE;
}

// A copy of socket.gethostname() from socketmodule.c.  That module brings in
// too many dependencies.

static PyObject *errno_error;

static PyObject *
socket_gethostname(PyObject *self, PyObject *unused)
{
    char buf[1024];
    int res;
    Py_BEGIN_ALLOW_THREADS
    res = gethostname(buf, (int) sizeof buf - 1);
    //res = gethostname(buf, 0);  // For testing errors
    Py_END_ALLOW_THREADS
    if (res < 0)
        return PyErr_SetFromErrno(errno_error);
    buf[sizeof buf - 1] = '\0';
    return PyString_FromString(buf);
}

static PyObject *
func_get_terminal_width(PyObject *self, PyObject *unused) {
  struct winsize w;
  int res;
  res = ioctl(STDOUT_FILENO, TIOCGWINSZ, &w);
  if (res < 0)
    return PyErr_SetFromErrno(errno_error);
  return PyLong_FromLong(w.ws_col);
}

static PyObject *
func_wcswidth(PyObject *self, PyObject *args){
    char *string;
    if (!PyArg_ParseTuple(args, "s", &string)) {
        return NULL;
    }

    const char *old_locale = setlocale(LC_CTYPE, NULL);
    if (setlocale(LC_CTYPE, "en_US.UTF-8") == NULL) {
        PyErr_SetString(PyExc_SystemError, "en_US.UTF-8 is not a valid locale");
        return NULL;
    }
    int len = mbstowcs(NULL, string, 0);
    if (len == -1) {
        PyErr_SetString(PyExc_UnicodeError, "mbstowcs error: Invalid UTF-8 string");
        setlocale(LC_CTYPE, old_locale);
        return NULL;
    }
    wchar_t unicode[len + 1];
    mbstowcs(unicode, string, len + 1);
    int width = wcswidth(unicode, len + 1);

    setlocale(LC_CTYPE, old_locale);
    return PyInt_FromLong(width);
}

#ifdef OVM_MAIN
#include "native/libc.c/methods.def"
#else
static PyMethodDef methods[] = {
  // Return the canonical version of a path with symlinks, or None if there is
  // an error.
  {"realpath", func_realpath, METH_VARARGS, ""},

  // Return whether a string matches a pattern."
  {"fnmatch", func_fnmatch, METH_VARARGS, ""},

  // Return a list of files that match a pattern.
  // We need this since Python's glob doesn't have char classes.
  {"glob", func_glob, METH_VARARGS, ""},

  // Compile a regex in ERE syntax, returning whether it is valid
  {"regex_parse", func_regex_parse, METH_VARARGS, ""},

  // Match regex against a string.  Returns a list of matches, None if no
  // match.  Raises RuntimeError if the regex is invalid.
  {"regex_match", func_regex_match, METH_VARARGS, ""},

  // If the regex matches the string, return the start and end position of the
  // first group.  Returns None if there is no match.  Raises RuntimeError if
  // the regex is invalid.
  {"regex_first_group_match", func_regex_first_group_match, METH_VARARGS, ""},

  // "Print three floating point values for the 'time' builtin.
  {"print_time", func_print_time, METH_VARARGS, ""},

  {"gethostname", socket_gethostname, METH_NOARGS, ""},

  // ioctl() to get the terminal width.
  {"get_terminal_width", func_get_terminal_width, METH_NOARGS, ""},

  // Get the display width of a string. Throw an exception if the string is invalid UTF8.
  {"wcswidth", func_wcswidth, METH_VARARGS, ""},
  {NULL, NULL},
};
#endif

void initlibc(void) {
  Py_InitModule("libc", methods);
  errno_error = PyErr_NewException("libc.error",
                                    PyExc_IOError, NULL);
}

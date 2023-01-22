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

  // TODO: Throw exception like IOError here
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

  int flags = 0;
  // NOTE: Testing for __GLIBC__ is the version detection anti-pattern.  We
  // should really use feature detection in our configure script.  But I plan
  // to get rid of the dependency on FNM_EXTMATCH because it doesn't work on
  // musl libc (or OS X).  Instead we should compile extended globs to extended
  // regex syntax.
#ifdef __GLIBC__
  flags |= FNM_EXTMATCH;
#else
  debug("Warning: FNM_EXTMATCH is not defined");
#endif

  int ret = fnmatch(pattern, str, flags);

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
    //fprintf(stderr, "func_glob: %s: %s\n", pattern, err_str);
    PyErr_SetString(PyExc_RuntimeError, err_str);
    return NULL;
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
  int status = regcomp(&pat, pattern, REG_EXTENDED);
  if (status != 0) {
    char error_string[80];
    regerror(status, &pat, error_string, 80);
    PyErr_SetString(PyExc_RuntimeError, error_string);
    return NULL;
  }
  regfree(&pat);

  Py_RETURN_TRUE;
}

static PyObject *
func_regex_match(PyObject *self, PyObject *args) {
  const char* pattern;
  const char* str;
  if (!PyArg_ParseTuple(args, "ss", &pattern, &str)) {
    return NULL;
  }

  regex_t pat;
  int status = regcomp(&pat, pattern, REG_EXTENDED);
  if (status != 0) {
    char error_string[80];
    regerror(status, &pat, error_string, 80);
    PyErr_SetString(PyExc_RuntimeError, error_string);
    return NULL;
  }

  int outlen = pat.re_nsub + 1;
  PyObject *ret = PyList_New(outlen);

  if (ret == NULL) {
    regfree(&pat);
    return NULL;
  }

  regmatch_t *pmatch = (regmatch_t*) malloc(sizeof(regmatch_t) * outlen);
  int match = regexec(&pat, str, outlen, pmatch, 0);
  if (match == 0) {
    int i;
    for (i = 0; i < outlen; i++) {
      int len = pmatch[i].rm_eo - pmatch[i].rm_so;
      PyObject *v = PyString_FromStringAndSize(str + pmatch[i].rm_so, len);
      PyList_SetItem(ret, i, v);
    }
  }

  free(pmatch);
  regfree(&pat);

  if (match != 0) {
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

  // Could have been checked by regex_parse for [[ =~ ]], but not for glob
  // patterns like ${foo/x*/y}.

  int status = regcomp(&pat, pattern, REG_EXTENDED);
  if (status != 0) {
    char error_string[80];
    regerror(status, &pat, error_string, 80);
    PyErr_SetString(PyExc_RuntimeError, error_string);
    return NULL;
  }

  debug("first_group_match pat %s str %s pos %d", pattern, str, pos);

  // Match at offset 'pos'
  int result = regexec(&pat, str + pos, NMATCH, m, 0 /*flags*/);
  regfree(&pat);

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

    int num_wide_chars = mbstowcs(NULL, string, 0);
    if (num_wide_chars == -1) {
        PyErr_SetString(PyExc_UnicodeError, "mbstowcs() 1");
        return NULL;
    }
    int buf_size = (num_wide_chars + 1) * sizeof(wchar_t);
    wchar_t* wide_chars = (wchar_t*)malloc(buf_size);
    assert(wide_chars != NULL);

    num_wide_chars = mbstowcs(wide_chars, string, num_wide_chars);
    if (num_wide_chars == -1) {
        PyErr_SetString(PyExc_UnicodeError, "mbstowcs() 2");
        return NULL;
    }

    int width = wcswidth(wide_chars, num_wide_chars);
    if (width == -1) {
        PyErr_SetString(PyExc_UnicodeError, "wcswidth()");
        return NULL;
    }

    return PyInt_FromLong(width);
}

static PyObject *
func_cpython_reset_locale(PyObject *self, PyObject *unused)
{
  if (setlocale(LC_CTYPE, "en_US.UTF-8") == NULL) {
    if (setlocale(LC_CTYPE, "C.UTF-8") == NULL) {
	    PyErr_SetString(PyExc_SystemError,
                      "Couldn't set locale to en_US.UTF-8 or C.UTF-8");
  	  return NULL;
    }
  }

  Py_RETURN_NONE;
}

#ifdef OVM_MAIN
#include "pyext/libc.c/methods.def"
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

  // Workaround for CPython's calling setlocale() in pythonrun.c.  ONLY used
  // by tests and bin/oil.py.
  {"cpython_reset_locale", func_cpython_reset_locale, METH_NOARGS, ""},
  {NULL, NULL},
};
#endif

void initlibc(void) {
  Py_InitModule("libc", methods);
  errno_error = PyErr_NewException("libc.error",
                                    PyExc_IOError, NULL);
}

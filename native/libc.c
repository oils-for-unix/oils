/*
Copyright 2014 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

/*
 * _fastrand.c -- Python extension module to generate random bit vectors
 * quickly.
 *
 * IMPORTANT: This module does not use crytographically strong randomness.  It
 * should be used ONLY be used to speed up the simulation.  Don't use it in
 * production.
 *
 * If an adversary can predict which random bits are flipped, then RAPPOR's
 * privacy is compromised.
 *
 */

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // printf

#include <fnmatch.h>
#include <glob.h>
#ifdef __FreeBSD__
#include <gnu/posix/regex.h>
#else
include <regex.h>
#endif

#include <Python.h>

// Log messages to stderr.
void debug(const char* fmt, ...) {
#ifdef LIBC_VERBOSE
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
#endif
}

static PyObject *
func_fnmatch(PyObject *self, PyObject *args) {
  const char *pattern;
  const char *str;

  if (!PyArg_ParseTuple(args, "ss", &pattern, &str)) {
    return NULL;
  }

  int flags = 0;
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
int globerr(const char *path, int eerrno) {
  fprintf(stderr, "%s: %s\n", path, strerror(eerrno));
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
  int ret = glob(pattern, flags, globerr, &results);

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
    fprintf(stderr, "%s: %s\n", pattern, err_str);
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
    // TODO: return a proper value?
    fprintf(stderr, "Error compiling regex: %s\n", err_str);
    Py_RETURN_FALSE;
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
  regmatch_t m[2];

  // Should have been checked by regex_parse
  if (regcomp(&pat, pattern, REG_EXTENDED) != 0) {
    fprintf(stderr, "Invalid regex at runtime\n");
    return PyLong_FromLong(-1);
  }
  //regcomp(&pat, pattern, REG_EXTENDED);

  int ret;
  // must match at pos 0
  if (regexec(&pat, str, 2, m, 0) == 0) {
    debug("MATCH\n");
  //if (regexec(&pat, str, 2, m, 0) == 0 && !m[0].rm_so) {
    // Return first parenthesized subexpression as string, or length of match

    /*
    if (pat.re_nsub>0) {
      ret->s = xmprintf("%.*s", m[1].rm_eo-m[1].rm_so, target+m[1].rm_so);
      if (TT.refree) free(TT.refree);
      TT.refree = ret->s;
    } else assign_int(ret, m[0].rm_eo);
    */
    ret = 1;

  } else {
    debug("NO MATCH");
    /*
    if (pat.re_nsub>0) ret->s = "";
    else assign_int(ret, 0);
    */
    ret = 0;
  }
  regfree(&pat);

  // TODO: Return a list for BASH_REMATCH.

  if (ret) {
    return PyLong_FromLong(1);
  } else {
    Py_RETURN_FALSE;
    return PyLong_FromLong(0);
  }
}

PyMethodDef methods[] = {
  {"fnmatch", func_fnmatch, METH_VARARGS,
   "Return whether a string matches a pattern."},
  // Python's glob doesn't have char classes
  {"glob", func_glob, METH_VARARGS,
   "Return files that match a pattern."},
  // https://docs.python.org/2/c-api/capsule.html#capsules
  {"regex_parse", func_regex_parse, METH_VARARGS,
   "Compile a regex in ERE syntax, returning whether it is valid"},
  {"regex_match", func_regex_match, METH_VARARGS,
   "Match regex against a string, returning a list of matches"},
  {NULL, NULL},
};

void initlibc(void) {
  Py_InitModule("libc", methods);
}

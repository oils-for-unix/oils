/**
 * Implement the python library stubs
 */

#include "Python.h"

#include <unistd.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


int Py_VerboseFlag = 1;
int Py_DebugFlag = 0;


// Error
void Py_FatalError(const char *err) {
  fprintf(stderr, "Fatal: %s", err);
  exit(-1);
}

// XXX: replace this with our arena allocator...
void *PyMem_MALLOC(size_t size) {
  return malloc(size);
}

// XXX: ...so that we won't even need this.
void PyMem_FREE(void *ptr) {
  free(ptr);
}

// XXX: same as above.
void *PyMem_REALLOC(void * ptr, size_t size) {
  return realloc(ptr, size);
}

// XXX: same as above.
void *PyObject_MALLOC(size_t size) {
  return malloc(size);
}

// XXX: same as above.
void *PyObject_REALLOC(void * ptr, size_t size) {
  return realloc(ptr, size);
}

// XXX: ...so that we won't even need this.
void PyObject_FREE(void *ptr) {
  free(ptr);
}


// Readline ... but for now don't use interactive prompt.
char *PyOS_Readline(FILE *in, FILE *out, char *prompt) {
  Py_FatalError("PyOS_Readline: NOT IMPLEMENTED");
  exit(-1);
  return NULL;
}


void PyOS_snprintf(char *buf, size_t n, const char *fmt, ...) {
  Py_FatalError("PyOS_snprintf: NOT IMPLEMENTED");
  exit(-1);
}

void PySys_WriteStdout(const char *format, ...) {
    va_list va;

    va_start(va, format);
    vfprintf(stdout, format, va);
    va_end(va);
}

void PySys_WriteStderr(const char *format, ...) {
    va_list va;

    va_start(va, format);
    vfprintf(stderr, format, va);
    va_end(va);
}

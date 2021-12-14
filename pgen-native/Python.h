#ifndef __PYTHON_H__
#define __PYTHON_H__

/**
 * Stub out the bits of python on which which parser.c depends.
 *
 */

#include <assert.h>
#include <ctype.h>
#include <limits.h>
#include <stdbool.h>
//#include <stddef.h>
#include <unistd.h>
// XXX: Remove instances of these later
#define PyAPI_FUNC(x) extern x
#define PyAPI_DATA(x) extern x

#define PY_SIZE_MAX SSIZE_MAX

// Define this, because it's true.
#define PGEN

// Types
typedef ssize_t Py_ssize_t;

extern int Py_VerboseFlag;
extern int Py_DebugFlag;


void Py_FatalError(const char *err);

void *PyMem_MALLOC(size_t size);
void  PyMem_FREE(void *ptr);
void *PyMem_REALLOC(void * ptr, size_t size);
void *PyObject_MALLOC(size_t size);
void *PyObject_REALLOC(void * ptr, size_t size);
void  PyObject_FREE(void *ptr);

void PyOS_snprintf(char *buf, size_t n, const char *fmt, ...);
void PySys_WriteStdout(const char *format, ...);
void PySys_WriteStderr(const char *format, ...);


// This copied straight from the headers.
/* Argument must be a char or an int in [-128, 127] or [0, 255]. */
#define Py_CHARMASK(c) ((unsigned char)((c) & 0xff))

// not sure about this one
#if USE_PY_CTYPE
#define Py_ISALPHA(c)  (_Py_ctype_table[Py_CHARMASK(c)] & PY_CTF_ALPHA)
#else
#define Py_ISALPHA(c) isalpha(c)
#define Py_ISALNUM(c) isalnum(c)
#endif

#endif

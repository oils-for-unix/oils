#include "Python.h"

// Notes on thread-local state that objects use (PyThreadState)
//
// Py_EnterRecursiveCall / Py_LeaveRecursiveCall -- so we don't blow the stack
// Py_ReprEnter / Py_ReprLeave -- for printing [...] in self-referential structures
//
// PyErr_Occurred -- check for exceptions, stubbed in pgenmain
// PyErr_CheckSignals -- for OS signals, stubbed in sigcheck.c, and here
//
// Notes on builtins like int().  See Python/bltinmodule.c.
//
// #define SETBUILTIN(NAME, OBJECT) \
//     if (PyDict_SetItemString(dict, NAME, (PyObject *)OBJECT) < 0)       \
//         return NULL;                                                    \
//     ADD_TO_ALL(OBJECT)
//
// SETBUILTIN("int",                   &PyInt_Type);
//
// It creates the __builtin__ module, which has a __dict__.  And then the types
// are here.   So you can just call a type directly?  Sure.

// #include "longintrepr.h"  // 32 bytes

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // vprintf

void Log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  printf("\n");
}


int Py_VerboseFlag; /* pythonrun.c, does only intobject.c use it? */

PyThreadState *_PyThreadState_Current = NULL;

struct _inittab _PyImport_Inittab[] = {
    /* Sentinel */
    {0, 0}
};

void
Py_FatalError(const char *msg)
{
    fprintf(stderr, "Fatal Python error: %s\n", msg);
    abort();
}

/* Even smaller than Python/sigcheck.c */
int
PyErr_CheckSignals(void)
{
	return 0;
}

/* APIs to write to sys.stdout or sys.stderr using a printf-like interface.
   Adapted from code submitted by Just van Rossum.

   PySys_WriteStdout(format, ...)
   PySys_WriteStderr(format, ...)

      The first function writes to sys.stdout; the second to sys.stderr.  When
      there is a problem, they write to the real (C level) stdout or stderr;
      no exceptions are raised.

      Both take a printf-style format string as their first argument followed
      by a variable length argument list determined by the format string.

      *** WARNING ***

      The format should limit the total size of the formatted output string to
      1000 bytes.  In particular, this means that no unrestricted "%s" formats
      should occur; these should be limited using "%.<N>s where <N> is a
      decimal number calculated so that <N> plus the maximum size of other
      formatted text does not exceed 1000 bytes.  Also watch out for "%f",
      which can print hundreds of digits for very large numbers.

 */

static void
mywrite(char *name, FILE *fp, const char *format, va_list va)
{
#ifdef OBJECTS_ONLY
    assert(0);
#else
    PyObject *file;
    PyObject *error_type, *error_value, *error_traceback;

    PyErr_Fetch(&error_type, &error_value, &error_traceback);
    file = PySys_GetObject(name);
    if (file == NULL || PyFile_AsFile(file) == fp)
        vfprintf(fp, format, va);
    else {
        char buffer[1001];
        const int written = PyOS_vsnprintf(buffer, sizeof(buffer),
                                           format, va);
        if (PyFile_WriteString(buffer, file) != 0) {
            PyErr_Clear();
            fputs(buffer, fp);
        }
        if (written < 0 || (size_t)written >= sizeof(buffer)) {
            const char *truncated = "... truncated";
            if (PyFile_WriteString(truncated, file) != 0) {
                PyErr_Clear();
                fputs(truncated, fp);
            }
        }
    }
    PyErr_Restore(error_type, error_value, error_traceback);
#endif
}

/*
void
PySys_WriteStdout(const char *format, ...)
{
    va_list va;

    va_start(va, format);
    mywrite("stdout", stdout, format, va);
    va_end(va);
}
*/

void
PySys_WriteStderr(const char *format, ...)
{
    va_list va;

    va_start(va, format);
    mywrite("stderr", stderr, format, va);
    va_end(va);
}


#define FILE_BEGIN_ALLOW_THREADS(fobj)
#define FILE_END_ALLOW_THREADS(fobj)

static PyObject *
err_closed(void)
{
    PyErr_SetString(PyExc_ValueError, "I/O operation on closed file");
    return NULL;
}

/* Interfaces to write objects/strings to file-like objects */

int
PyFile_WriteObject(PyObject *v, PyObject *f, int flags)
{
#ifdef OBJECTS_ONLY
    assert(0);
#else
    PyObject *writer, *value, *args, *result;
    if (f == NULL) {
        PyErr_SetString(PyExc_TypeError, "writeobject with NULL file");
        return -1;
    }
    else if (PyFile_Check(f)) {
        PyFileObject *fobj = (PyFileObject *) f;
#ifdef Py_USING_UNICODE
        PyObject *enc = fobj->f_encoding;
        int result;
#endif
        if (fobj->f_fp == NULL) {
            err_closed();
            return -1;
        }
#ifdef Py_USING_UNICODE
        if ((flags & Py_PRINT_RAW) &&
            PyUnicode_Check(v) && enc != Py_None) {
            char *cenc = PyString_AS_STRING(enc);
            char *errors = fobj->f_errors == Py_None ?
              "strict" : PyString_AS_STRING(fobj->f_errors);
            value = PyUnicode_AsEncodedString(v, cenc, errors);
            if (value == NULL)
                return -1;
        } else {
            value = v;
            Py_INCREF(value);
        }
        result = file_PyObject_Print(value, fobj, flags);
        Py_DECREF(value);
        return result;
#else
        return file_PyObject_Print(v, fobj, flags);
#endif
    }
    writer = PyObject_GetAttrString(f, "write");
    if (writer == NULL)
        return -1;
    if (flags & Py_PRINT_RAW) {
        if (PyUnicode_Check(v)) {
            value = v;
            Py_INCREF(value);
        } else
            value = PyObject_Str(v);
    }
    else
        value = PyObject_Repr(v);
    if (value == NULL) {
        Py_DECREF(writer);
        return -1;
    }
    args = PyTuple_Pack(1, value);
    if (args == NULL) {
        Py_DECREF(value);
        Py_DECREF(writer);
        return -1;
    }
    result = PyEval_CallObject(writer, args);
    Py_DECREF(args);
    Py_DECREF(value);
    Py_DECREF(writer);
    if (result == NULL)
        return -1;
    Py_DECREF(result);
#endif
    return 0;
}

int
PyFile_WriteString(const char *s, PyObject *f)
{
#ifdef OBJECTS_ONLY
    assert(0);
#else
    if (f == NULL) {
        /* Should be caused by a pre-existing error */
        if (!PyErr_Occurred())
            PyErr_SetString(PyExc_SystemError,
                            "null file for PyFile_WriteString");
        return -1;
    }
    else if (PyFile_Check(f)) {
        PyFileObject *fobj = (PyFileObject *) f;
        FILE *fp = PyFile_AsFile(f);
        if (fp == NULL) {
            err_closed();
            return -1;
        }
        FILE_BEGIN_ALLOW_THREADS(fobj)
        fputs(s, fp);
        FILE_END_ALLOW_THREADS(fobj)
        return 0;
    }
    else if (!PyErr_Occurred()) {
        PyObject *v = PyString_FromString(s);
        int err;
        if (v == NULL)
            return -1;
        err = PyFile_WriteObject(v, f, Py_PRINT_RAW);
        Py_DECREF(v);
        return err;
    }
    else
        return -1;
#endif
}


/* Stub of function in Python/_warnings.c */
int
PyErr_WarnEx(PyObject *category, const char *text, Py_ssize_t stack_level)
{
  return 0;
}

/* from Python/ceval.c */

#define Py_DEFAULT_RECURSION_LIMIT 1000
/* a lot of code uses this too */
int _Py_CheckRecursionLimit = Py_DEFAULT_RECURSION_LIMIT;

int
Py_GetRecursionLimit(void)
{
    return Py_DEFAULT_RECURSION_LIMIT;
}

void
Py_SetRecursionLimit(int new_limit)
{
}

int
_Py_CheckRecursiveCall(const char *where)
{
  return 0;
}

/* Extract a slice index from a PyInt or PyLong or an object with the
   nb_index slot defined, and store in *pi.
   Silently reduce values larger than PY_SSIZE_T_MAX to PY_SSIZE_T_MAX,
   and silently boost values less than -PY_SSIZE_T_MAX-1 to -PY_SSIZE_T_MAX-1.
   Return 0 on error, 1 on success.
*/
/* Note:  If v is NULL, return success without storing into *pi.  This
   is because_PyEval_SliceIndex() is called by apply_slice(), which can be
   called by the SLICE opcode with v and/or w equal to NULL.
*/
int
_PyEval_SliceIndex(PyObject *v, Py_ssize_t *pi)
{
    if (v != NULL) {
        Py_ssize_t x;
        if (PyInt_Check(v)) {
            /* XXX(nnorwitz): I think PyInt_AS_LONG is correct,
               however, it looks like it should be AsSsize_t.
               There should be a comment here explaining why.
            */
            x = PyInt_AS_LONG(v);
        }
        else if (PyIndex_Check(v)) {
            x = PyNumber_AsSsize_t(v, NULL);
            if (x == -1 && PyErr_Occurred())
                return 0;
        }
        else {
            PyErr_SetString(PyExc_TypeError,
                            "slice indices must be integers or "
                            "None or have an __index__ method");
            return 0;
        }
        *pi = x;
    }
    return 1;
}

/* External interface to call any callable object.
   The arg must be a tuple or NULL.  The kw must be a dict or NULL. */

PyObject *
PyEval_CallObjectWithKeywords(PyObject *func, PyObject *arg, PyObject *kw)
{
    PyObject *result;

    if (arg == NULL) {
        arg = PyTuple_New(0);
        if (arg == NULL)
            return NULL;
    }
    else if (!PyTuple_Check(arg)) {
        PyErr_SetString(PyExc_TypeError,
                        "argument list must be a tuple");
        return NULL;
    }
    else
        Py_INCREF(arg);

    if (kw != NULL && !PyDict_Check(kw)) {
        PyErr_SetString(PyExc_TypeError,
                        "keyword list must be a dictionary");
        Py_DECREF(arg);
        return NULL;
    }

    result = PyObject_Call(func, arg, kw);
    Py_DECREF(arg);
    return result;
}

/* NOTE: Can't use a switch here because it's not an integer constant!
 *
 * Instead of "with tagswitch", do "with typeswitch"?
 * */

void Type(PyObject* obj) {
    struct _typeobject* type = obj->ob_type;

    if (type == &PyBool_Type) {
        Log("bool");
    } else if (type == &PyLong_Type) {
        Log("long");
    } else if (type == &PyFloat_Type) {
        Log("float");
    } else if (type == &PyString_Type) {
        Log("string");
    } else if (type == &PyTuple_Type) {
        Log("tuple");
    } else if (type == &PyList_Type) {
        Log("list");
    } else if (type == &PyDict_Type) {
        Log("dict");
    } else {
        Log("unknown type");
    }
}

void PrintList(reprfunc list_repr, PyObject* list) {
  PyObject* r = list_repr(list);
  assert(r != NULL);
  PyStringObject* rstr = (PyStringObject*) r;

  fprintf(stderr, "list = %.*s\n", (int)rstr->ob_size, rstr->ob_sval);
}

int main(int argc, char **argv) {
  PyObject* bool1 = PyBool_FromLong(1);

  reprfunc bool_repr = PyBool_Type.tp_repr;
  PyObject* b = bool_repr(bool1);

  PyStringObject* br = (PyStringObject*) b;

  fprintf(stderr, "true = %.*s\n", (int)br->ob_size, br->ob_sval);


  PyObject* long1 = PyLong_FromLong(42);
  PyObject* long2 = PyLong_FromLong(1);

  binaryfunc long_add = PyLong_Type.tp_as_number->nb_add;
  PyObject* long_sum = long_add(long1, long2);

  reprfunc long_repr = PyLong_Type.tp_repr;
  PyObject* r = long_repr(long_sum);

  PyStringObject* rstr = (PyStringObject*) r;

  fprintf(stderr, "42 + 1 = %.*s\n", (int)rstr->ob_size, rstr->ob_sval);


  PyObject* float1 = PyFloat_FromDouble(42.1);
  PyObject* float2 = PyFloat_FromDouble(1.2);

  binaryfunc float_add = PyFloat_Type.tp_as_number->nb_add;
  PyObject* float_sum = float_add(float1, float2);

  reprfunc float_repr = PyFloat_Type.tp_repr;
  PyObject* r3 = float_repr(float_sum);

  PyStringObject* rstr3 = (PyStringObject*) r3;

  fprintf(stderr, "42.1 + 1.2 = %.*s\n", (int)rstr3->ob_size, rstr3->ob_sval);


  PyObject* str1 = PyString_FromString("foo ");
  PyObject* str2 = PyString_FromString("bar");

  binaryfunc str_add = PyString_Type.tp_as_sequence->sq_concat;
  PyObject* concat = str_add(str1, str2);

  reprfunc str_repr = PyString_Type.tp_repr;
  PyObject* r2 = str_repr(concat);

  PyStringObject* rstr2 = (PyStringObject*) r2;

  fprintf(stderr, "foo + bar = %.*s\n", (int)rstr2->ob_size, rstr2->ob_sval);

  // List

  PyObject* list = PyList_New(3);
  PyList_SetItem(list, 0, long_sum);
  PyList_SetItem(list, 1, float_sum);
  /* Test the printing of cyclic data structures */
  PyList_SetItem(list, 2, list);

  reprfunc list_repr = PyList_Type.tp_repr;
  PyObject* r5 = list_repr(list);
  assert(r5 != NULL);
  PyStringObject* rstr5 = (PyStringObject*) r5;

  fprintf(stderr, "list = %.*s\n", (int)rstr5->ob_size, rstr5->ob_sval);

  Log("");

  // Sort and reverse list
  PyObject* list2 = PyList_New(3);
  PyList_SetItem(list2, 0, long1);
  PyList_SetItem(list2, 1, long2);
  PyList_SetItem(list2, 2, long_sum);
  PrintList(list_repr, list2);

  // These are internal API calls.  listsort() and listreverse() are in the
  // method table, and do less work.
  PyList_Sort(list2);
  PrintList(list_repr, list2);

  PyList_Reverse(list2);
  PrintList(list_repr, list2);

  /* Works if you make it non-static
  listreverse(list2);
  PrintList(list_repr, list2);
  */

  Log("");

  // Tuple

  PyObject* tuple = PyTuple_New(3);
  PyTuple_SetItem(tuple, 0, long_sum);
  PyTuple_SetItem(tuple, 1, float_sum);
  PyTuple_SetItem(tuple, 2, concat);

  reprfunc tuple_repr = PyTuple_Type.tp_repr;
  PyObject* r4 = tuple_repr(tuple);
  assert(r4 != NULL);

  PyStringObject* rstr4 = (PyStringObject*) r4;

  fprintf(stderr, "tuple = %.*s\n", (int)rstr4->ob_size, rstr4->ob_sval);

  // Dict

  PyObject* dict = PyDict_New();
  PyDict_SetItem(dict, concat, long_sum);

  reprfunc dict_repr = PyDict_Type.tp_repr;
  PyObject* d = dict_repr(dict);
  assert(d != NULL);

  PyStringObject* dr = (PyStringObject*) d;

  fprintf(stderr, "dict = %.*s\n", (int)dr->ob_size, dr->ob_sval);

  // suceess
  PyObject* val = PyDict_GetItem(dict, concat);
  Log("val = %p", val);

  // fail
  PyObject* val2 = PyDict_GetItem(dict, long1);
  Log("val2 = %p", val2);
  // TODO: How to get exception?

  Type(long_sum);
  Type(float_sum);
  Type(list);
  Type(dict);

  Log("sizeof(PyBoolObject) = %zu", sizeof(PyBoolObject));  // 24
  // 32 bytes, needs header
  //Log("sizeof(PyLongObject) = %zu", sizeof(PyLongObject));
  Log("sizeof(PyFloatObject) = %zu", sizeof(PyFloatObject));  // 24
  Log("sizeof(PyStringObject) = %zu", sizeof(PyStringObject));  // 40
  Log("sizeof(PyTupleObject) = %zu", sizeof(PyTupleObject));  // 32
  Log("sizeof(PyListObject) = %zu", sizeof(PyListObject));  // 40
  Log("sizeof(PyDictObject) = %zu", sizeof(PyDictObject));  // 248


  // TODO:
  // - Iterate over dicts and lists
  // - Call methods -- how?
  //   - .keys() and .value() -- see addmethods()
  //   - respect calling convention flags for L.sort() and L.reverse()
  // - Test exceptions like IndexError, KeyError, and more
  // - Other types: slices?  What about range and enumeration?
  // - repr(None)?  How?  Py_None
  //   object.c has PyNone_Type, but it's not in a header!
  // - builtins like int() str()
	return 0;
}

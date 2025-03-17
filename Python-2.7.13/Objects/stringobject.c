/* String (str/bytes) object implementation */

#define PY_SSIZE_T_CLEAN

#include "Python.h"
#include <ctype.h>
#include <stddef.h>

#ifdef COUNT_ALLOCS
Py_ssize_t null_strings, one_strings;
#endif

static PyStringObject *characters[UCHAR_MAX + 1];
static PyStringObject *nullstring;

/* This dictionary holds all interned strings.  Note that references to
   strings in this dictionary are *not* counted in the string's ob_refcnt.
   When the interned string reaches a refcnt of 0 the string deallocation
   function will delete the reference from this dictionary.

   Another way to look at this is that to say that the actual reference
   count of a string is:  s->ob_refcnt + (s->ob_sstate?2:0)
*/
static PyObject *interned;

/* PyStringObject_SIZE gives the basic size of a string; any memory allocation
   for a string of length n should request PyStringObject_SIZE + n bytes.

   Using PyStringObject_SIZE instead of sizeof(PyStringObject) saves
   3 bytes per string allocation on a typical system.
*/
#define PyStringObject_SIZE (offsetof(PyStringObject, ob_sval) + 1)

/*
   For PyString_FromString(), the parameter `str' points to a null-terminated
   string containing exactly `size' bytes.

   For PyString_FromStringAndSize(), the parameter `str' is
   either NULL or else points to a string containing at least `size' bytes.
   For PyString_FromStringAndSize(), the string in the `str' parameter does
   not have to be null-terminated.  (Therefore it is safe to construct a
   substring by calling `PyString_FromStringAndSize(origstring, substrlen)'.)
   If `str' is NULL then PyString_FromStringAndSize() will allocate `size+1'
   bytes (setting the last byte to the null terminating character) and you can
   fill in the data yourself.  If `str' is non-NULL then the resulting
   PyString object must be treated as immutable and you must not fill in nor
   alter the data yourself, since the strings may be shared.

   The PyObject member `op->ob_size', which denotes the number of "extra
   items" in a variable-size object, will contain the number of bytes
   allocated for string data, not counting the null terminating character.
   It is therefore equal to the `size' parameter (for
   PyString_FromStringAndSize()) or the length of the string in the `str'
   parameter (for PyString_FromString()).
*/
PyObject *
PyString_FromStringAndSize(const char *str, Py_ssize_t size)
{
    register PyStringObject *op;
    if (size < 0) {
        PyErr_SetString(PyExc_SystemError,
            "Negative size passed to PyString_FromStringAndSize");
        return NULL;
    }
    if (size == 0 && (op = nullstring) != NULL) {
#ifdef COUNT_ALLOCS
        null_strings++;
#endif
        Py_INCREF(op);
        return (PyObject *)op;
    }
    if (size == 1 && str != NULL &&
        (op = characters[*str & UCHAR_MAX]) != NULL)
    {
#ifdef COUNT_ALLOCS
        one_strings++;
#endif
        Py_INCREF(op);
        return (PyObject *)op;
    }

    if (size > PY_SSIZE_T_MAX - PyStringObject_SIZE) {
        PyErr_SetString(PyExc_OverflowError, "string is too large");
        return NULL;
    }

    /* Inline PyObject_NewVar */
    op = (PyStringObject *)PyObject_MALLOC(PyStringObject_SIZE + size);
    if (op == NULL)
        return PyErr_NoMemory();
    (void)PyObject_INIT_VAR(op, &PyString_Type, size);
    op->ob_shash = -1;
    op->ob_sstate = SSTATE_NOT_INTERNED;
    if (str != NULL)
        Py_MEMCPY(op->ob_sval, str, size);
    op->ob_sval[size] = '\0';
    /* share short strings */
    if (size == 0) {
        PyObject *t = (PyObject *)op;
        PyString_InternInPlace(&t);
        op = (PyStringObject *)t;
        nullstring = op;
        Py_INCREF(op);
    } else if (size == 1 && str != NULL) {
        PyObject *t = (PyObject *)op;
        PyString_InternInPlace(&t);
        op = (PyStringObject *)t;
        characters[*str & UCHAR_MAX] = op;
        Py_INCREF(op);
    }
    return (PyObject *) op;
}

PyObject *
PyString_FromString(const char *str)
{
    register size_t size;
    register PyStringObject *op;

    assert(str != NULL);
    size = strlen(str);
    if (size > PY_SSIZE_T_MAX - PyStringObject_SIZE) {
        PyErr_SetString(PyExc_OverflowError,
            "string is too long for a Python string");
        return NULL;
    }
    if (size == 0 && (op = nullstring) != NULL) {
#ifdef COUNT_ALLOCS
        null_strings++;
#endif
        Py_INCREF(op);
        return (PyObject *)op;
    }
    if (size == 1 && (op = characters[*str & UCHAR_MAX]) != NULL) {
#ifdef COUNT_ALLOCS
        one_strings++;
#endif
        Py_INCREF(op);
        return (PyObject *)op;
    }

    /* Inline PyObject_NewVar */
    op = (PyStringObject *)PyObject_MALLOC(PyStringObject_SIZE + size);
    if (op == NULL)
        return PyErr_NoMemory();
    (void)PyObject_INIT_VAR(op, &PyString_Type, size);
    op->ob_shash = -1;
    op->ob_sstate = SSTATE_NOT_INTERNED;
    Py_MEMCPY(op->ob_sval, str, size+1);
    /* share short strings */
    if (size == 0) {
        PyObject *t = (PyObject *)op;
        PyString_InternInPlace(&t);
        op = (PyStringObject *)t;
        nullstring = op;
        Py_INCREF(op);
    } else if (size == 1) {
        PyObject *t = (PyObject *)op;
        PyString_InternInPlace(&t);
        op = (PyStringObject *)t;
        characters[*str & UCHAR_MAX] = op;
        Py_INCREF(op);
    }
    return (PyObject *) op;
}

PyObject *
PyString_FromFormatV(const char *format, va_list vargs)
{
    va_list count;
    Py_ssize_t n = 0;
    const char* f;
    char *s;
    PyObject* string;

#ifdef VA_LIST_IS_ARRAY
    Py_MEMCPY(count, vargs, sizeof(va_list));
#else
#ifdef  __va_copy
    __va_copy(count, vargs);
#else
    count = vargs;
#endif
#endif
    /* step 1: figure out how large a buffer we need */
    for (f = format; *f; f++) {
        if (*f == '%') {
#ifdef HAVE_LONG_LONG
            int longlongflag = 0;
#endif
            const char* p = f;
            while (*++f && *f != '%' && !isalpha(Py_CHARMASK(*f)))
                ;

            /* skip the 'l' or 'z' in {%ld, %zd, %lu, %zu} since
             * they don't affect the amount of space we reserve.
             */
            if (*f == 'l') {
                if (f[1] == 'd' || f[1] == 'u') {
                    ++f;
                }
#ifdef HAVE_LONG_LONG
                else if (f[1] == 'l' &&
                         (f[2] == 'd' || f[2] == 'u')) {
                    longlongflag = 1;
                    f += 2;
                }
#endif
            }
            else if (*f == 'z' && (f[1] == 'd' || f[1] == 'u')) {
                ++f;
            }

            switch (*f) {
            case 'c':
                (void)va_arg(count, int);
                /* fall through... */
            case '%':
                n++;
                break;
            case 'd': case 'u': case 'i': case 'x':
                (void) va_arg(count, int);
#ifdef HAVE_LONG_LONG
                /* Need at most
                   ceil(log10(256)*SIZEOF_LONG_LONG) digits,
                   plus 1 for the sign.  53/22 is an upper
                   bound for log10(256). */
                if (longlongflag)
                    n += 2 + (SIZEOF_LONG_LONG*53-1) / 22;
                else
#endif
                    /* 20 bytes is enough to hold a 64-bit
                       integer.  Decimal takes the most
                       space.  This isn't enough for
                       octal. */
                    n += 20;

                break;
            case 's':
                s = va_arg(count, char*);
                n += strlen(s);
                break;
            case 'p':
                (void) va_arg(count, int);
                /* maximum 64-bit pointer representation:
                 * 0xffffffffffffffff
                 * so 19 characters is enough.
                 * XXX I count 18 -- what's the extra for?
                 */
                n += 19;
                break;
            default:
                /* if we stumble upon an unknown
                   formatting code, copy the rest of
                   the format string to the output
                   string. (we cannot just skip the
                   code, since there's no way to know
                   what's in the argument list) */
                n += strlen(p);
                goto expand;
            }
        } else
            n++;
    }
 expand:
    /* step 2: fill the buffer */
    /* Since we've analyzed how much space we need for the worst case,
       use sprintf directly instead of the slower PyOS_snprintf. */
    string = PyString_FromStringAndSize(NULL, n);
    if (!string)
        return NULL;

    s = PyString_AsString(string);

    for (f = format; *f; f++) {
        if (*f == '%') {
            const char* p = f++;
            Py_ssize_t i;
            int longflag = 0;
#ifdef HAVE_LONG_LONG
            int longlongflag = 0;
#endif
            int size_tflag = 0;
            /* parse the width.precision part (we're only
               interested in the precision value, if any) */
            n = 0;
            while (isdigit(Py_CHARMASK(*f)))
                n = (n*10) + *f++ - '0';
            if (*f == '.') {
                f++;
                n = 0;
                while (isdigit(Py_CHARMASK(*f)))
                    n = (n*10) + *f++ - '0';
            }
            while (*f && *f != '%' && !isalpha(Py_CHARMASK(*f)))
                f++;
            /* Handle %ld, %lu, %lld and %llu. */
            if (*f == 'l') {
                if (f[1] == 'd' || f[1] == 'u') {
                    longflag = 1;
                    ++f;
                }
#ifdef HAVE_LONG_LONG
                else if (f[1] == 'l' &&
                         (f[2] == 'd' || f[2] == 'u')) {
                    longlongflag = 1;
                    f += 2;
                }
#endif
            }
            /* handle the size_t flag. */
            else if (*f == 'z' && (f[1] == 'd' || f[1] == 'u')) {
                size_tflag = 1;
                ++f;
            }

            switch (*f) {
            case 'c':
                *s++ = va_arg(vargs, int);
                break;
            case 'd':
                if (longflag)
                    sprintf(s, "%ld", va_arg(vargs, long));
#ifdef HAVE_LONG_LONG
                else if (longlongflag)
                    sprintf(s, "%" PY_FORMAT_LONG_LONG "d",
                        va_arg(vargs, PY_LONG_LONG));
#endif
                else if (size_tflag)
                    sprintf(s, "%" PY_FORMAT_SIZE_T "d",
                        va_arg(vargs, Py_ssize_t));
                else
                    sprintf(s, "%d", va_arg(vargs, int));
                s += strlen(s);
                break;
            case 'u':
                if (longflag)
                    sprintf(s, "%lu",
                        va_arg(vargs, unsigned long));
#ifdef HAVE_LONG_LONG
                else if (longlongflag)
                    sprintf(s, "%" PY_FORMAT_LONG_LONG "u",
                        va_arg(vargs, PY_LONG_LONG));
#endif
                else if (size_tflag)
                    sprintf(s, "%" PY_FORMAT_SIZE_T "u",
                        va_arg(vargs, size_t));
                else
                    sprintf(s, "%u",
                        va_arg(vargs, unsigned int));
                s += strlen(s);
                break;
            case 'i':
                sprintf(s, "%i", va_arg(vargs, int));
                s += strlen(s);
                break;
            case 'x':
                sprintf(s, "%x", va_arg(vargs, int));
                s += strlen(s);
                break;
            case 's':
                p = va_arg(vargs, char*);
                i = strlen(p);
                if (n > 0 && i > n)
                    i = n;
                Py_MEMCPY(s, p, i);
                s += i;
                break;
            case 'p':
                sprintf(s, "%p", va_arg(vargs, void*));
                /* %p is ill-defined:  ensure leading 0x. */
                if (s[1] == 'X')
                    s[1] = 'x';
                else if (s[1] != 'x') {
                    memmove(s+2, s, strlen(s)+1);
                    s[0] = '0';
                    s[1] = 'x';
                }
                s += strlen(s);
                break;
            case '%':
                *s++ = '%';
                break;
            default:
                strcpy(s, p);
                s += strlen(s);
                goto end;
            }
        } else
            *s++ = *f;
    }

 end:
    if (_PyString_Resize(&string, s - PyString_AS_STRING(string)))
        return NULL;
    return string;
}

PyObject *
PyString_FromFormat(const char *format, ...)
{
    PyObject* ret;
    va_list vargs;

#ifdef HAVE_STDARG_PROTOTYPES
    va_start(vargs, format);
#else
    va_start(vargs);
#endif
    ret = PyString_FromFormatV(format, vargs);
    va_end(vargs);
    return ret;
}


#ifndef OVM_MAIN
PyObject *PyString_Decode(const char *s,
                          Py_ssize_t size,
                          const char *encoding,
                          const char *errors)
{
    PyObject *v, *str;

    str = PyString_FromStringAndSize(s, size);
    if (str == NULL)
        return NULL;
    v = PyString_AsDecodedString(str, encoding, errors);
    Py_DECREF(str);
    return v;
}

PyObject *PyString_AsDecodedObject(PyObject *str,
                                   const char *encoding,
                                   const char *errors)
{
    PyObject *v;

    if (!PyString_Check(str)) {
        PyErr_BadArgument();
        goto onError;
    }

    if (encoding == NULL) {
#ifdef Py_USING_UNICODE
        encoding = PyUnicode_GetDefaultEncoding();
#else
        PyErr_SetString(PyExc_ValueError, "no encoding specified");
        goto onError;
#endif
    }

    /* Decode via the codec registry */
    v = _PyCodec_DecodeText(str, encoding, errors);
    if (v == NULL)
        goto onError;

    return v;

 onError:
    return NULL;
}

PyObject *PyString_AsDecodedString(PyObject *str,
                                   const char *encoding,
                                   const char *errors)
{
    PyObject *v;

    v = PyString_AsDecodedObject(str, encoding, errors);
    if (v == NULL)
        goto onError;

#ifdef Py_USING_UNICODE
    /* Convert Unicode to a string using the default encoding */
    if (PyUnicode_Check(v)) {
        PyObject *temp = v;
        v = PyUnicode_AsEncodedString(v, NULL, NULL);
        Py_DECREF(temp);
        if (v == NULL)
            goto onError;
    }
#endif
    if (!PyString_Check(v)) {
        PyErr_Format(PyExc_TypeError,
                     "decoder did not return a string object (type=%.400s)",
                     Py_TYPE(v)->tp_name);
        Py_DECREF(v);
        goto onError;
    }

    return v;

 onError:
    return NULL;
}

PyObject *PyString_Encode(const char *s,
                          Py_ssize_t size,
                          const char *encoding,
                          const char *errors)
{
    PyObject *v, *str;

    str = PyString_FromStringAndSize(s, size);
    if (str == NULL)
        return NULL;
    v = PyString_AsEncodedString(str, encoding, errors);
    Py_DECREF(str);
    return v;
}

PyObject *PyString_AsEncodedObject(PyObject *str,
                                   const char *encoding,
                                   const char *errors)
{
    PyObject *v;

    if (!PyString_Check(str)) {
        PyErr_BadArgument();
        goto onError;
    }

    if (encoding == NULL) {
#ifdef Py_USING_UNICODE
        encoding = PyUnicode_GetDefaultEncoding();
#else
        PyErr_SetString(PyExc_ValueError, "no encoding specified");
        goto onError;
#endif
    }

    /* Encode via the codec registry */
    v = _PyCodec_EncodeText(str, encoding, errors);
    if (v == NULL)
        goto onError;

    return v;

 onError:
    return NULL;
}

PyObject *PyString_AsEncodedString(PyObject *str,
                                   const char *encoding,
                                   const char *errors)
{
    PyObject *v;

    v = PyString_AsEncodedObject(str, encoding, errors);
    if (v == NULL)
        goto onError;

#ifdef Py_USING_UNICODE
    /* Convert Unicode to a string using the default encoding */
    if (PyUnicode_Check(v)) {
        PyObject *temp = v;
        v = PyUnicode_AsEncodedString(v, NULL, NULL);
        Py_DECREF(temp);
        if (v == NULL)
            goto onError;
    }
#endif
    if (!PyString_Check(v)) {
        PyErr_Format(PyExc_TypeError,
                     "encoder did not return a string object (type=%.400s)",
                     Py_TYPE(v)->tp_name);
        Py_DECREF(v);
        goto onError;
    }

    return v;

 onError:
    return NULL;
}
#endif

static void
string_dealloc(PyObject *op)
{
    switch (PyString_CHECK_INTERNED(op)) {
        case SSTATE_NOT_INTERNED:
            break;

        case SSTATE_INTERNED_MORTAL:
            /* revive dead object temporarily for DelItem */
            Py_REFCNT(op) = 3;
            if (PyDict_DelItem(interned, op) != 0)
                Py_FatalError(
                    "deletion of interned string failed");
            break;

        case SSTATE_INTERNED_IMMORTAL:
            Py_FatalError("Immortal interned string died.");

        default:
            Py_FatalError("Inconsistent interned string state.");
    }
    Py_TYPE(op)->tp_free(op);
}

/* Unescape a backslash-escaped string. If unicode is non-zero,
   the string is a u-literal. If recode_encoding is non-zero,
   the string is UTF-8 encoded and should be re-encoded in the
   specified encoding.  */

PyObject *PyString_DecodeEscape(const char *s,
                                Py_ssize_t len,
                                const char *errors,
                                Py_ssize_t unicode,
                                const char *recode_encoding)
{
    int c;
    char *p, *buf;
    const char *end;
    PyObject *v;
    Py_ssize_t newlen = recode_encoding ? 4*len:len;
    v = PyString_FromStringAndSize((char *)NULL, newlen);
    if (v == NULL)
        return NULL;
    p = buf = PyString_AsString(v);
    end = s + len;
    while (s < end) {
        if (*s != '\\') {
          non_esc:
#ifdef Py_USING_UNICODE
            if (recode_encoding && (*s & 0x80)) {
                PyObject *u, *w;
                char *r;
                const char* t;
                Py_ssize_t rn;
                t = s;
                /* Decode non-ASCII bytes as UTF-8. */
                while (t < end && (*t & 0x80)) t++;
                u = PyUnicode_DecodeUTF8(s, t - s, errors);
                if(!u) goto failed;

                /* Recode them in target encoding. */
                w = PyUnicode_AsEncodedString(
                    u, recode_encoding, errors);
                Py_DECREF(u);
                if (!w)                 goto failed;

                /* Append bytes to output buffer. */
                assert(PyString_Check(w));
                r = PyString_AS_STRING(w);
                rn = PyString_GET_SIZE(w);
                Py_MEMCPY(p, r, rn);
                p += rn;
                Py_DECREF(w);
                s = t;
            } else {
                *p++ = *s++;
            }
#else
            *p++ = *s++;
#endif
            continue;
        }
        s++;
        if (s==end) {
            PyErr_SetString(PyExc_ValueError,
                            "Trailing \\ in string");
            goto failed;
        }
        switch (*s++) {
        /* XXX This assumes ASCII! */
        case '\n': break;
        case '\\': *p++ = '\\'; break;
        case '\'': *p++ = '\''; break;
        case '\"': *p++ = '\"'; break;
        case 'b': *p++ = '\b'; break;
        case 'f': *p++ = '\014'; break; /* FF */
        case 't': *p++ = '\t'; break;
        case 'n': *p++ = '\n'; break;
        case 'r': *p++ = '\r'; break;
        case 'v': *p++ = '\013'; break; /* VT */
        case 'a': *p++ = '\007'; break; /* BEL, not classic C */
        case '0': case '1': case '2': case '3':
        case '4': case '5': case '6': case '7':
            c = s[-1] - '0';
            if (s < end && '0' <= *s && *s <= '7') {
                c = (c<<3) + *s++ - '0';
                if (s < end && '0' <= *s && *s <= '7')
                    c = (c<<3) + *s++ - '0';
            }
            *p++ = c;
            break;
        case 'x':
            if (s+1 < end &&
                isxdigit(Py_CHARMASK(s[0])) &&
                isxdigit(Py_CHARMASK(s[1])))
            {
                unsigned int x = 0;
                c = Py_CHARMASK(*s);
                s++;
                if (isdigit(c))
                    x = c - '0';
                else if (islower(c))
                    x = 10 + c - 'a';
                else
                    x = 10 + c - 'A';
                x = x << 4;
                c = Py_CHARMASK(*s);
                s++;
                if (isdigit(c))
                    x += c - '0';
                else if (islower(c))
                    x += 10 + c - 'a';
                else
                    x += 10 + c - 'A';
                *p++ = x;
                break;
            }
            if (!errors || strcmp(errors, "strict") == 0) {
                PyErr_SetString(PyExc_ValueError,
                                "invalid \\x escape");
                goto failed;
            }
            if (strcmp(errors, "replace") == 0) {
                *p++ = '?';
            } else if (strcmp(errors, "ignore") == 0)
                /* do nothing */;
            else {
                PyErr_Format(PyExc_ValueError,
                             "decoding error; "
                             "unknown error handling code: %.400s",
                             errors);
                goto failed;
            }
            /* skip \x */
            if (s < end && isxdigit(Py_CHARMASK(s[0])))
                s++; /* and a hexdigit */
            break;
#ifndef Py_USING_UNICODE
        case 'u':
        case 'U':
        case 'N':
            if (unicode) {
                PyErr_SetString(PyExc_ValueError,
                          "Unicode escapes not legal "
                          "when Unicode disabled");
                goto failed;
            }
#endif
        default:
            *p++ = '\\';
            s--;
            goto non_esc; /* an arbitrary number of unescaped
                             UTF-8 bytes may follow. */
        }
    }
    if (p-buf < newlen)
        _PyString_Resize(&v, p - buf); /* v is cleared on error */
    return v;
  failed:
    Py_DECREF(v);
    return NULL;
}

/* -------------------------------------------------------------------- */
/* object api */

static Py_ssize_t
string_getsize(register PyObject *op)
{
    char *s;
    Py_ssize_t len;
    if (PyString_AsStringAndSize(op, &s, &len))
        return -1;
    return len;
}

static /*const*/ char *
string_getbuffer(register PyObject *op)
{
    char *s;
    Py_ssize_t len;
    if (PyString_AsStringAndSize(op, &s, &len))
        return NULL;
    return s;
}

Py_ssize_t
PyString_Size(register PyObject *op)
{
    if (!PyString_Check(op))
        return string_getsize(op);
    return Py_SIZE(op);
}

/*const*/ char *
PyString_AsString(register PyObject *op)
{
    if (!PyString_Check(op))
        return string_getbuffer(op);
    return ((PyStringObject *)op) -> ob_sval;
}

int
PyString_AsStringAndSize(register PyObject *obj,
                         register char **s,
                         register Py_ssize_t *len)
{
    if (s == NULL) {
        PyErr_BadInternalCall();
        return -1;
    }

    if (!PyString_Check(obj)) {
#ifdef Py_USING_UNICODE
        if (PyUnicode_Check(obj)) {
            obj = _PyUnicode_AsDefaultEncodedString(obj, NULL);
            if (obj == NULL)
                return -1;
        }
        else
#endif
        {
            PyErr_Format(PyExc_TypeError,
                         "expected string or Unicode object, "
                         "%.200s found", Py_TYPE(obj)->tp_name);
            return -1;
        }
    }

    *s = PyString_AS_STRING(obj);
    if (len != NULL)
        *len = PyString_GET_SIZE(obj);
    else if (strlen(*s) != (size_t)PyString_GET_SIZE(obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "expected string without null bytes");
        return -1;
    }
    return 0;
}

/* -------------------------------------------------------------------- */
/* Methods */

#include "stringlib/stringdefs.h"
#include "stringlib/fastsearch.h"

#include "stringlib/count.h"
#include "stringlib/find.h"
#include "stringlib/partition.h"
#include "stringlib/split.h"

#define _Py_InsertThousandsGrouping _PyString_InsertThousandsGrouping
#include "stringlib/localeutil.h"



static int
string_print(PyStringObject *op, FILE *fp, int flags)
{
    Py_ssize_t i, str_len;
    char c;
    int quote;

    /* XXX Ought to check for interrupts when writing long strings */
    if (! PyString_CheckExact(op)) {
        int ret;
        /* A str subclass may have its own __str__ method. */
        op = (PyStringObject *) PyObject_Str((PyObject *)op);
        if (op == NULL)
            return -1;
        ret = string_print(op, fp, flags);
        Py_DECREF(op);
        return ret;
    }
    if (flags & Py_PRINT_RAW) {
        char *data = op->ob_sval;
        Py_ssize_t size = Py_SIZE(op);
        Py_BEGIN_ALLOW_THREADS
        while (size > INT_MAX) {
            /* Very long strings cannot be written atomically.
             * But don't write exactly INT_MAX bytes at a time
             * to avoid memory aligment issues.
             */
            const int chunk_size = INT_MAX & ~0x3FFF;
            fwrite(data, 1, chunk_size, fp);
            data += chunk_size;
            size -= chunk_size;
        }
#ifdef __VMS
        if (size) fwrite(data, (size_t)size, 1, fp);
#else
        fwrite(data, 1, (size_t)size, fp);
#endif
        Py_END_ALLOW_THREADS
        return 0;
    }

    /* figure out which quote to use; single is preferred */
    quote = '\'';
    if (memchr(op->ob_sval, '\'', Py_SIZE(op)) &&
        !memchr(op->ob_sval, '"', Py_SIZE(op)))
        quote = '"';

    str_len = Py_SIZE(op);
    Py_BEGIN_ALLOW_THREADS
    fputc(quote, fp);
    for (i = 0; i < str_len; i++) {
        /* Since strings are immutable and the caller should have a
        reference, accessing the internal buffer should not be an issue
        with the GIL released. */
        c = op->ob_sval[i];
        if (c == quote || c == '\\')
            fprintf(fp, "\\%c", c);
        else if (c == '\t')
            fprintf(fp, "\\t");
        else if (c == '\n')
            fprintf(fp, "\\n");
        else if (c == '\r')
            fprintf(fp, "\\r");
        else if (c < ' ' || c >= 0x7f)
            fprintf(fp, "\\x%02x", c & 0xff);
        else
            fputc(c, fp);
    }
    fputc(quote, fp);
    Py_END_ALLOW_THREADS
    return 0;
}

PyObject *
PyString_Repr(PyObject *obj, int smartquotes)
{
    register PyStringObject* op = (PyStringObject*) obj;
    size_t newsize;
    PyObject *v;
    if (Py_SIZE(op) > (PY_SSIZE_T_MAX - 2)/4) {
        PyErr_SetString(PyExc_OverflowError,
            "string is too large to make repr");
        return NULL;
    }
    newsize = 2 + 4*Py_SIZE(op);
    v = PyString_FromStringAndSize((char *)NULL, newsize);
    if (v == NULL) {
        return NULL;
    }
    else {
        register Py_ssize_t i;
        register char c;
        register char *p;
        int quote;

        /* figure out which quote to use; single is preferred */
        quote = '\'';
        if (smartquotes &&
            memchr(op->ob_sval, '\'', Py_SIZE(op)) &&
            !memchr(op->ob_sval, '"', Py_SIZE(op)))
            quote = '"';

        p = PyString_AS_STRING(v);
        *p++ = quote;
        for (i = 0; i < Py_SIZE(op); i++) {
            /* There's at least enough room for a hex escape
               and a closing quote. */
            assert(newsize - (p - PyString_AS_STRING(v)) >= 5);
            c = op->ob_sval[i];
            if (c == quote || c == '\\')
                *p++ = '\\', *p++ = c;
            else if (c == '\t')
                *p++ = '\\', *p++ = 't';
            else if (c == '\n')
                *p++ = '\\', *p++ = 'n';
            else if (c == '\r')
                *p++ = '\\', *p++ = 'r';
            else if (c < ' ' || c >= 0x7f) {
                /* For performance, we don't want to call
                   PyOS_snprintf here (extra layers of
                   function call). */
                sprintf(p, "\\x%02x", c & 0xff);
                p += 4;
            }
            else
                *p++ = c;
        }
        assert(newsize - (p - PyString_AS_STRING(v)) >= 1);
        *p++ = quote;
        *p = '\0';
        if (_PyString_Resize(&v, (p - PyString_AS_STRING(v))))
            return NULL;
        return v;
    }
}

static PyObject *
string_repr(PyObject *op)
{
    return PyString_Repr(op, 1);
}

static PyObject *
string_str(PyObject *s)
{
    assert(PyString_Check(s));
    if (PyString_CheckExact(s)) {
        Py_INCREF(s);
        return s;
    }
    else {
        /* Subtype -- return genuine string with the same value. */
        PyStringObject *t = (PyStringObject *) s;
        return PyString_FromStringAndSize(t->ob_sval, Py_SIZE(t));
    }
}

static Py_ssize_t
string_length(PyStringObject *a)
{
    return Py_SIZE(a);
}

static PyObject *
string_concat(register PyStringObject *a, register PyObject *bb)
{
    register Py_ssize_t size;
    register PyStringObject *op;
    if (!PyString_Check(bb)) {
#ifdef Py_USING_UNICODE
        if (PyUnicode_Check(bb))
            return PyUnicode_Concat((PyObject *)a, bb);
#endif
#ifndef OVM_MAIN
        if (PyByteArray_Check(bb))
            return PyByteArray_Concat((PyObject *)a, bb);
#endif
        PyErr_Format(PyExc_TypeError,
                     "cannot concatenate 'str' and '%.200s' objects",
                     Py_TYPE(bb)->tp_name);
        return NULL;
    }
#define b ((PyStringObject *)bb)
    /* Optimize cases with empty left or right operand */
    if ((Py_SIZE(a) == 0 || Py_SIZE(b) == 0) &&
        PyString_CheckExact(a) && PyString_CheckExact(b)) {
        if (Py_SIZE(a) == 0) {
            Py_INCREF(bb);
            return bb;
        }
        Py_INCREF(a);
        return (PyObject *)a;
    }
    /* Check that string sizes are not negative, to prevent an
       overflow in cases where we are passed incorrectly-created
       strings with negative lengths (due to a bug in other code).
    */
    if (Py_SIZE(a) < 0 || Py_SIZE(b) < 0 ||
        Py_SIZE(a) > PY_SSIZE_T_MAX - Py_SIZE(b)) {
        PyErr_SetString(PyExc_OverflowError,
                        "strings are too large to concat");
        return NULL;
    }
    size = Py_SIZE(a) + Py_SIZE(b);

    /* Inline PyObject_NewVar */
    if (size > PY_SSIZE_T_MAX - PyStringObject_SIZE) {
        PyErr_SetString(PyExc_OverflowError,
                        "strings are too large to concat");
        return NULL;
    }
    op = (PyStringObject *)PyObject_MALLOC(PyStringObject_SIZE + size);
    if (op == NULL)
        return PyErr_NoMemory();
    (void)PyObject_INIT_VAR(op, &PyString_Type, size);
    op->ob_shash = -1;
    op->ob_sstate = SSTATE_NOT_INTERNED;
    Py_MEMCPY(op->ob_sval, a->ob_sval, Py_SIZE(a));
    Py_MEMCPY(op->ob_sval + Py_SIZE(a), b->ob_sval, Py_SIZE(b));
    op->ob_sval[size] = '\0';
    return (PyObject *) op;
#undef b
}

static PyObject *
string_repeat(register PyStringObject *a, register Py_ssize_t n)
{
    register Py_ssize_t i;
    register Py_ssize_t j;
    register Py_ssize_t size;
    register PyStringObject *op;
    size_t nbytes;
    if (n < 0)
        n = 0;
    /* watch out for overflows:  the size can overflow Py_ssize_t,
     * and the # of bytes needed can overflow size_t
     */
    if (n && Py_SIZE(a) > PY_SSIZE_T_MAX / n) {
        PyErr_SetString(PyExc_OverflowError,
            "repeated string is too long");
        return NULL;
    }
    size = Py_SIZE(a) * n;
    if (size == Py_SIZE(a) && PyString_CheckExact(a)) {
        Py_INCREF(a);
        return (PyObject *)a;
    }
    nbytes = (size_t)size;
    if (nbytes + PyStringObject_SIZE <= nbytes) {
        PyErr_SetString(PyExc_OverflowError,
            "repeated string is too long");
        return NULL;
    }
    op = (PyStringObject *)PyObject_MALLOC(PyStringObject_SIZE + nbytes);
    if (op == NULL)
        return PyErr_NoMemory();
    (void)PyObject_INIT_VAR(op, &PyString_Type, size);
    op->ob_shash = -1;
    op->ob_sstate = SSTATE_NOT_INTERNED;
    op->ob_sval[size] = '\0';
    if (Py_SIZE(a) == 1 && n > 0) {
        memset(op->ob_sval, a->ob_sval[0] , n);
        return (PyObject *) op;
    }
    i = 0;
    if (i < size) {
        Py_MEMCPY(op->ob_sval, a->ob_sval, Py_SIZE(a));
        i = Py_SIZE(a);
    }
    while (i < size) {
        j = (i <= size-i)  ?  i  :  size-i;
        Py_MEMCPY(op->ob_sval+i, op->ob_sval, j);
        i += j;
    }
    return (PyObject *) op;
}

/* String slice a[i:j] consists of characters a[i] ... a[j-1] */

static PyObject *
string_slice(register PyStringObject *a, register Py_ssize_t i,
             register Py_ssize_t j)
     /* j -- may be negative! */
{
    if (i < 0)
        i = 0;
    if (j < 0)
        j = 0; /* Avoid signed/unsigned bug in next line */
    if (j > Py_SIZE(a))
        j = Py_SIZE(a);
    if (i == 0 && j == Py_SIZE(a) && PyString_CheckExact(a)) {
        /* It's the same as a */
        Py_INCREF(a);
        return (PyObject *)a;
    }
    if (j < i)
        j = i;
    return PyString_FromStringAndSize(a->ob_sval + i, j-i);
}

static int
string_contains(PyObject *str_obj, PyObject *sub_obj)
{
    if (!PyString_CheckExact(sub_obj)) {
#ifdef Py_USING_UNICODE
        if (PyUnicode_Check(sub_obj))
            return PyUnicode_Contains(str_obj, sub_obj);
#endif
        if (!PyString_Check(sub_obj)) {
            PyErr_Format(PyExc_TypeError,
                "'in <string>' requires string as left operand, "
                "not %.200s", Py_TYPE(sub_obj)->tp_name);
            return -1;
        }
    }

    return stringlib_contains_obj(str_obj, sub_obj);
}

static PyObject *
string_item(PyStringObject *a, register Py_ssize_t i)
{
    char pchar;
    PyObject *v;
    if (i < 0 || i >= Py_SIZE(a)) {
        PyErr_SetString(PyExc_IndexError, "string index out of range");
        return NULL;
    }
    pchar = a->ob_sval[i];
    v = (PyObject *)characters[pchar & UCHAR_MAX];
    if (v == NULL)
        v = PyString_FromStringAndSize(&pchar, 1);
    else {
#ifdef COUNT_ALLOCS
        one_strings++;
#endif
        Py_INCREF(v);
    }
    return v;
}

static PyObject*
string_richcompare(PyStringObject *a, PyStringObject *b, int op)
{
    int c;
    Py_ssize_t len_a, len_b;
    Py_ssize_t min_len;
    PyObject *result;

    /* Make sure both arguments are strings. */
    if (!(PyString_Check(a) && PyString_Check(b))) {
        result = Py_NotImplemented;
        goto out;
    }
    if (a == b) {
        switch (op) {
        case Py_EQ:case Py_LE:case Py_GE:
            result = Py_True;
            goto out;
        case Py_NE:case Py_LT:case Py_GT:
            result = Py_False;
            goto out;
        }
    }
    if (op == Py_EQ) {
        /* Supporting Py_NE here as well does not save
           much time, since Py_NE is rarely used.  */
        if (Py_SIZE(a) == Py_SIZE(b)
            && (a->ob_sval[0] == b->ob_sval[0]
            && memcmp(a->ob_sval, b->ob_sval, Py_SIZE(a)) == 0)) {
            result = Py_True;
        } else {
            result = Py_False;
        }
        goto out;
    }
    len_a = Py_SIZE(a); len_b = Py_SIZE(b);
    min_len = (len_a < len_b) ? len_a : len_b;
    if (min_len > 0) {
        c = Py_CHARMASK(*a->ob_sval) - Py_CHARMASK(*b->ob_sval);
        if (c==0)
            c = memcmp(a->ob_sval, b->ob_sval, min_len);
    } else
        c = 0;
    if (c == 0)
        c = (len_a < len_b) ? -1 : (len_a > len_b) ? 1 : 0;
    switch (op) {
    case Py_LT: c = c <  0; break;
    case Py_LE: c = c <= 0; break;
    case Py_EQ: assert(0);  break; /* unreachable */
    case Py_NE: c = c != 0; break;
    case Py_GT: c = c >  0; break;
    case Py_GE: c = c >= 0; break;
    default:
        result = Py_NotImplemented;
        goto out;
    }
    result = c ? Py_True : Py_False;
  out:
    Py_INCREF(result);
    return result;
}

int
_PyString_Eq(PyObject *o1, PyObject *o2)
{
    PyStringObject *a = (PyStringObject*) o1;
    PyStringObject *b = (PyStringObject*) o2;
    return Py_SIZE(a) == Py_SIZE(b)
      && memcmp(a->ob_sval, b->ob_sval, Py_SIZE(a)) == 0;
}

static long
string_hash(PyStringObject *a)
{
    register Py_ssize_t len;
    register unsigned char *p;
    register long x;

#ifdef Py_DEBUG
    assert(_Py_HashSecret_Initialized);
#endif
    if (a->ob_shash != -1)
        return a->ob_shash;
    len = Py_SIZE(a);
    /*
      We make the hash of the empty string be 0, rather than using
      (prefix ^ suffix), since this slightly obfuscates the hash secret
    */
    if (len == 0) {
        a->ob_shash = 0;
        return 0;
    }
    p = (unsigned char *) a->ob_sval;
    x = _Py_HashSecret.prefix;
    x ^= *p << 7;
    while (--len >= 0)
        x = (1000003*x) ^ *p++;
    x ^= Py_SIZE(a);
    x ^= _Py_HashSecret.suffix;
    if (x == -1)
        x = -2;
    a->ob_shash = x;
    return x;
}

static PyObject*
string_subscript(PyStringObject* self, PyObject* item)
{
    if (PyIndex_Check(item)) {
        Py_ssize_t i = PyNumber_AsSsize_t(item, PyExc_IndexError);
        if (i == -1 && PyErr_Occurred())
            return NULL;
        if (i < 0)
            i += PyString_GET_SIZE(self);
        return string_item(self, i);
    }
    else if (PySlice_Check(item)) {
        Py_ssize_t start, stop, step, slicelength, cur, i;
        char* source_buf;
        char* result_buf;
        PyObject* result;

        if (PySlice_GetIndicesEx((PySliceObject*)item,
                         PyString_GET_SIZE(self),
                         &start, &stop, &step, &slicelength) < 0) {
            return NULL;
        }

        if (slicelength <= 0) {
            return PyString_FromStringAndSize("", 0);
        }
        else if (start == 0 && step == 1 &&
                 slicelength == PyString_GET_SIZE(self) &&
                 PyString_CheckExact(self)) {
            Py_INCREF(self);
            return (PyObject *)self;
        }
        else if (step == 1) {
            return PyString_FromStringAndSize(
                PyString_AS_STRING(self) + start,
                slicelength);
        }
        else {
            source_buf = PyString_AsString((PyObject*)self);
            result_buf = (char *)PyMem_Malloc(slicelength);
            if (result_buf == NULL)
                return PyErr_NoMemory();

            for (cur = start, i = 0; i < slicelength;
                 cur += step, i++) {
                result_buf[i] = source_buf[cur];
            }

            result = PyString_FromStringAndSize(result_buf,
                                                slicelength);
            PyMem_Free(result_buf);
            return result;
        }
    }
    else {
        PyErr_Format(PyExc_TypeError,
                     "string indices must be integers, not %.200s",
                     Py_TYPE(item)->tp_name);
        return NULL;
    }
}

static Py_ssize_t
string_buffer_getreadbuf(PyStringObject *self, Py_ssize_t index, const void **ptr)
{
    if ( index != 0 ) {
        PyErr_SetString(PyExc_SystemError,
                        "accessing non-existent string segment");
        return -1;
    }
    *ptr = (void *)self->ob_sval;
    return Py_SIZE(self);
}

static Py_ssize_t
string_buffer_getwritebuf(PyStringObject *self, Py_ssize_t index, const void **ptr)
{
    PyErr_SetString(PyExc_TypeError,
                    "Cannot use string as modifiable buffer");
    return -1;
}

static Py_ssize_t
string_buffer_getsegcount(PyStringObject *self, Py_ssize_t *lenp)
{
    if ( lenp )
        *lenp = Py_SIZE(self);
    return 1;
}

static Py_ssize_t
string_buffer_getcharbuf(PyStringObject *self, Py_ssize_t index, const char **ptr)
{
    if ( index != 0 ) {
        PyErr_SetString(PyExc_SystemError,
                        "accessing non-existent string segment");
        return -1;
    }
    *ptr = self->ob_sval;
    return Py_SIZE(self);
}

static int
string_buffer_getbuffer(PyStringObject *self, Py_buffer *view, int flags)
{
    return PyBuffer_FillInfo(view, (PyObject*)self,
                             (void *)self->ob_sval, Py_SIZE(self),
                             1, flags);
}

static PySequenceMethods string_as_sequence = {
    (lenfunc)string_length, /*sq_length*/
    (binaryfunc)string_concat, /*sq_concat*/
    (ssizeargfunc)string_repeat, /*sq_repeat*/
    (ssizeargfunc)string_item, /*sq_item*/
    (ssizessizeargfunc)string_slice, /*sq_slice*/
    0,                  /*sq_ass_item*/
    0,                  /*sq_ass_slice*/
    (objobjproc)string_contains /*sq_contains*/
};

static PyMappingMethods string_as_mapping = {
    (lenfunc)string_length,
    (binaryfunc)string_subscript,
    0,
};

static PyBufferProcs string_as_buffer = {
    (readbufferproc)string_buffer_getreadbuf,
    (writebufferproc)string_buffer_getwritebuf,
    (segcountproc)string_buffer_getsegcount,
    (charbufferproc)string_buffer_getcharbuf,
    (getbufferproc)string_buffer_getbuffer,
    0, /* XXX */
};



#define LEFTSTRIP 0
#define RIGHTSTRIP 1
#define BOTHSTRIP 2

/* Arrays indexed by above */
static const char *stripformat[] = {"|O:lstrip", "|O:rstrip", "|O:strip"};

#define STRIPNAME(i) (stripformat[i]+3)

PyDoc_STRVAR(split__doc__,
"S.split([sep [,maxsplit]]) -> list of strings\n\
\n\
Return a list of the words in the string S, using sep as the\n\
delimiter string.  If maxsplit is given, at most maxsplit\n\
splits are done. If sep is not specified or is None, any\n\
whitespace string is a separator and empty strings are removed\n\
from the result.");

static PyObject *
string_split(PyStringObject *self, PyObject *args)
{
    Py_ssize_t len = PyString_GET_SIZE(self), n;
    Py_ssize_t maxsplit = -1;
    const char *s = PyString_AS_STRING(self), *sub;
    PyObject *subobj = Py_None;

    if (!PyArg_ParseTuple(args, "|On:split", &subobj, &maxsplit))
        return NULL;
    if (maxsplit < 0)
        maxsplit = PY_SSIZE_T_MAX;
    if (subobj == Py_None)
        return stringlib_split_whitespace((PyObject*) self, s, len, maxsplit);
    if (PyString_Check(subobj)) {
        sub = PyString_AS_STRING(subobj);
        n = PyString_GET_SIZE(subobj);
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(subobj))
        return PyUnicode_Split((PyObject *)self, subobj, maxsplit);
#endif
    else if (PyObject_AsCharBuffer(subobj, &sub, &n))
        return NULL;

    return stringlib_split((PyObject*) self, s, len, sub, n, maxsplit);
}

PyDoc_STRVAR(partition__doc__,
"S.partition(sep) -> (head, sep, tail)\n\
\n\
Search for the separator sep in S, and return the part before it,\n\
the separator itself, and the part after it.  If the separator is not\n\
found, return S and two empty strings.");

static PyObject *
string_partition(PyStringObject *self, PyObject *sep_obj)
{
    const char *sep;
    Py_ssize_t sep_len;

    if (PyString_Check(sep_obj)) {
        sep = PyString_AS_STRING(sep_obj);
        sep_len = PyString_GET_SIZE(sep_obj);
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(sep_obj))
        return PyUnicode_Partition((PyObject *) self, sep_obj);
#endif
    else if (PyObject_AsCharBuffer(sep_obj, &sep, &sep_len))
        return NULL;

    return stringlib_partition(
        (PyObject*) self,
        PyString_AS_STRING(self), PyString_GET_SIZE(self),
        sep_obj, sep, sep_len
        );
}

PyDoc_STRVAR(rpartition__doc__,
"S.rpartition(sep) -> (head, sep, tail)\n\
\n\
Search for the separator sep in S, starting at the end of S, and return\n\
the part before it, the separator itself, and the part after it.  If the\n\
separator is not found, return two empty strings and S.");

static PyObject *
string_rpartition(PyStringObject *self, PyObject *sep_obj)
{
    const char *sep;
    Py_ssize_t sep_len;

    if (PyString_Check(sep_obj)) {
        sep = PyString_AS_STRING(sep_obj);
        sep_len = PyString_GET_SIZE(sep_obj);
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(sep_obj))
        return PyUnicode_RPartition((PyObject *) self, sep_obj);
#endif
    else if (PyObject_AsCharBuffer(sep_obj, &sep, &sep_len))
        return NULL;

    return stringlib_rpartition(
        (PyObject*) self,
        PyString_AS_STRING(self), PyString_GET_SIZE(self),
        sep_obj, sep, sep_len
        );
}

PyDoc_STRVAR(rsplit__doc__,
"S.rsplit([sep [,maxsplit]]) -> list of strings\n\
\n\
Return a list of the words in the string S, using sep as the\n\
delimiter string, starting at the end of the string and working\n\
to the front.  If maxsplit is given, at most maxsplit splits are\n\
done. If sep is not specified or is None, any whitespace string\n\
is a separator.");

static PyObject *
string_rsplit(PyStringObject *self, PyObject *args)
{
    Py_ssize_t len = PyString_GET_SIZE(self), n;
    Py_ssize_t maxsplit = -1;
    const char *s = PyString_AS_STRING(self), *sub;
    PyObject *subobj = Py_None;

    if (!PyArg_ParseTuple(args, "|On:rsplit", &subobj, &maxsplit))
        return NULL;
    if (maxsplit < 0)
        maxsplit = PY_SSIZE_T_MAX;
    if (subobj == Py_None)
        return stringlib_rsplit_whitespace((PyObject*) self, s, len, maxsplit);
    if (PyString_Check(subobj)) {
        sub = PyString_AS_STRING(subobj);
        n = PyString_GET_SIZE(subobj);
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(subobj))
        return PyUnicode_RSplit((PyObject *)self, subobj, maxsplit);
#endif
    else if (PyObject_AsCharBuffer(subobj, &sub, &n))
        return NULL;

    return stringlib_rsplit((PyObject*) self, s, len, sub, n, maxsplit);
}


PyDoc_STRVAR(join__doc__,
"S.join(iterable) -> string\n\
\n\
Return a string which is the concatenation of the strings in the\n\
iterable.  The separator between elements is S.");

static PyObject *
string_join(PyStringObject *self, PyObject *orig)
{
    char *sep = PyString_AS_STRING(self);
    const Py_ssize_t seplen = PyString_GET_SIZE(self);
    PyObject *res = NULL;
    char *p;
    Py_ssize_t seqlen = 0;
    size_t sz = 0;
    Py_ssize_t i;
    PyObject *seq, *item;

    seq = PySequence_Fast(orig, "can only join an iterable");
    if (seq == NULL) {
        return NULL;
    }

    seqlen = PySequence_Size(seq);
    if (seqlen == 0) {
        Py_DECREF(seq);
        return PyString_FromString("");
    }
    if (seqlen == 1) {
        item = PySequence_Fast_GET_ITEM(seq, 0);
#ifdef OVM_MAIN
        if (PyString_CheckExact(item)) {
#else
        if (PyString_CheckExact(item) || PyUnicode_CheckExact(item)) {
#endif
            Py_INCREF(item);
            Py_DECREF(seq);
            return item;
        }
    }

    /* There are at least two things to join, or else we have a subclass
     * of the builtin types in the sequence.
     * Do a pre-pass to figure out the total amount of space we'll
     * need (sz), see whether any argument is absurd, and defer to
     * the Unicode join if appropriate.
     */
    for (i = 0; i < seqlen; i++) {
        const size_t old_sz = sz;
        item = PySequence_Fast_GET_ITEM(seq, i);
        if (!PyString_Check(item)){
#ifdef Py_USING_UNICODE
            if (PyUnicode_Check(item)) {
                /* Defer to Unicode join.
                 * CAUTION:  There's no guarantee that the
                 * original sequence can be iterated over
                 * again, so we must pass seq here.
                 */
                PyObject *result;
                result = PyUnicode_Join((PyObject *)self, seq);
                Py_DECREF(seq);
                return result;
            }
#endif
            PyErr_Format(PyExc_TypeError,
                         "sequence item %zd: expected string,"
                         " %.80s found",
                         i, Py_TYPE(item)->tp_name);
            Py_DECREF(seq);
            return NULL;
        }
        sz += PyString_GET_SIZE(item);
        if (i != 0)
            sz += seplen;
        if (sz < old_sz || sz > PY_SSIZE_T_MAX) {
            PyErr_SetString(PyExc_OverflowError,
                "join() result is too long for a Python string");
            Py_DECREF(seq);
            return NULL;
        }
    }

    /* Allocate result space. */
    res = PyString_FromStringAndSize((char*)NULL, sz);
    if (res == NULL) {
        Py_DECREF(seq);
        return NULL;
    }

    /* Catenate everything. */
    p = PyString_AS_STRING(res);
    for (i = 0; i < seqlen; ++i) {
        size_t n;
        item = PySequence_Fast_GET_ITEM(seq, i);
        n = PyString_GET_SIZE(item);
        Py_MEMCPY(p, PyString_AS_STRING(item), n);
        p += n;
        if (i < seqlen - 1) {
            Py_MEMCPY(p, sep, seplen);
            p += seplen;
        }
    }

    Py_DECREF(seq);
    return res;
}

PyObject *
_PyString_Join(PyObject *sep, PyObject *x)
{
    assert(sep != NULL && PyString_Check(sep));
    assert(x != NULL);
    return string_join((PyStringObject *)sep, x);
}

/* helper macro to fixup start/end slice values */
#define ADJUST_INDICES(start, end, len)         \
    if (end > len)                          \
        end = len;                          \
    else if (end < 0) {                     \
        end += len;                         \
        if (end < 0)                        \
        end = 0;                        \
    }                                       \
    if (start < 0) {                        \
        start += len;                       \
        if (start < 0)                      \
        start = 0;                      \
    }

Py_LOCAL_INLINE(Py_ssize_t)
string_find_internal(PyStringObject *self, PyObject *args, int dir)
{
    PyObject *subobj;
    const char *sub;
    Py_ssize_t sub_len;
    Py_ssize_t start=0, end=PY_SSIZE_T_MAX;

    if (!stringlib_parse_args_finds("find/rfind/index/rindex",
                                    args, &subobj, &start, &end))
        return -2;

    if (PyString_Check(subobj)) {
        sub = PyString_AS_STRING(subobj);
        sub_len = PyString_GET_SIZE(subobj);
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(subobj))
        return PyUnicode_Find(
            (PyObject *)self, subobj, start, end, dir);
#endif
    else if (PyObject_AsCharBuffer(subobj, &sub, &sub_len))
        /* XXX - the "expected a character buffer object" is pretty
           confusing for a non-expert.  remap to something else ? */
        return -2;

    if (dir > 0)
        return stringlib_find_slice(
            PyString_AS_STRING(self), PyString_GET_SIZE(self),
            sub, sub_len, start, end);
    else
        return stringlib_rfind_slice(
            PyString_AS_STRING(self), PyString_GET_SIZE(self),
            sub, sub_len, start, end);
}


PyDoc_STRVAR(find__doc__,
"S.find(sub [,start [,end]]) -> int\n\
\n\
Return the lowest index in S where substring sub is found,\n\
such that sub is contained within S[start:end].  Optional\n\
arguments start and end are interpreted as in slice notation.\n\
\n\
Return -1 on failure.");

static PyObject *
string_find(PyStringObject *self, PyObject *args)
{
    Py_ssize_t result = string_find_internal(self, args, +1);
    if (result == -2)
        return NULL;
    return PyInt_FromSsize_t(result);
}


PyDoc_STRVAR(index__doc__,
"S.index(sub [,start [,end]]) -> int\n\
\n\
Like S.find() but raise ValueError when the substring is not found.");

static PyObject *
string_index(PyStringObject *self, PyObject *args)
{
    Py_ssize_t result = string_find_internal(self, args, +1);
    if (result == -2)
        return NULL;
    if (result == -1) {
        PyErr_SetString(PyExc_ValueError,
                        "substring not found");
        return NULL;
    }
    return PyInt_FromSsize_t(result);
}


PyDoc_STRVAR(rfind__doc__,
"S.rfind(sub [,start [,end]]) -> int\n\
\n\
Return the highest index in S where substring sub is found,\n\
such that sub is contained within S[start:end].  Optional\n\
arguments start and end are interpreted as in slice notation.\n\
\n\
Return -1 on failure.");

static PyObject *
string_rfind(PyStringObject *self, PyObject *args)
{
    Py_ssize_t result = string_find_internal(self, args, -1);
    if (result == -2)
        return NULL;
    return PyInt_FromSsize_t(result);
}


PyDoc_STRVAR(rindex__doc__,
"S.rindex(sub [,start [,end]]) -> int\n\
\n\
Like S.rfind() but raise ValueError when the substring is not found.");

static PyObject *
string_rindex(PyStringObject *self, PyObject *args)
{
    Py_ssize_t result = string_find_internal(self, args, -1);
    if (result == -2)
        return NULL;
    if (result == -1) {
        PyErr_SetString(PyExc_ValueError,
                        "substring not found");
        return NULL;
    }
    return PyInt_FromSsize_t(result);
}


Py_LOCAL_INLINE(PyObject *)
do_xstrip(PyStringObject *self, int striptype, PyObject *sepobj)
{
    char *s = PyString_AS_STRING(self);
    Py_ssize_t len = PyString_GET_SIZE(self);
    char *sep = PyString_AS_STRING(sepobj);
    Py_ssize_t seplen = PyString_GET_SIZE(sepobj);
    Py_ssize_t i, j;

    i = 0;
    if (striptype != RIGHTSTRIP) {
        while (i < len && memchr(sep, Py_CHARMASK(s[i]), seplen)) {
            i++;
        }
    }

    j = len;
    if (striptype != LEFTSTRIP) {
        do {
            j--;
        } while (j >= i && memchr(sep, Py_CHARMASK(s[j]), seplen));
        j++;
    }

    if (i == 0 && j == len && PyString_CheckExact(self)) {
        Py_INCREF(self);
        return (PyObject*)self;
    }
    else
        return PyString_FromStringAndSize(s+i, j-i);
}


Py_LOCAL_INLINE(PyObject *)
do_strip(PyStringObject *self, int striptype)
{
    char *s = PyString_AS_STRING(self);
    Py_ssize_t len = PyString_GET_SIZE(self), i, j;

    i = 0;
    if (striptype != RIGHTSTRIP) {
        while (i < len && isspace(Py_CHARMASK(s[i]))) {
            i++;
        }
    }

    j = len;
    if (striptype != LEFTSTRIP) {
        do {
            j--;
        } while (j >= i && isspace(Py_CHARMASK(s[j])));
        j++;
    }

    if (i == 0 && j == len && PyString_CheckExact(self)) {
        Py_INCREF(self);
        return (PyObject*)self;
    }
    else
        return PyString_FromStringAndSize(s+i, j-i);
}


Py_LOCAL_INLINE(PyObject *)
do_argstrip(PyStringObject *self, int striptype, PyObject *args)
{
    PyObject *sep = NULL;

    if (!PyArg_ParseTuple(args, (char *)stripformat[striptype], &sep))
        return NULL;

    if (sep != NULL && sep != Py_None) {
        if (PyString_Check(sep))
            return do_xstrip(self, striptype, sep);
#ifdef Py_USING_UNICODE
        else if (PyUnicode_Check(sep)) {
            PyObject *uniself = PyUnicode_FromObject((PyObject *)self);
            PyObject *res;
            if (uniself==NULL)
                return NULL;
            res = _PyUnicode_XStrip((PyUnicodeObject *)uniself,
                striptype, sep);
            Py_DECREF(uniself);
            return res;
        }
#endif
        PyErr_Format(PyExc_TypeError,
#ifdef Py_USING_UNICODE
                     "%s arg must be None, str or unicode",
#else
                     "%s arg must be None or str",
#endif
                     STRIPNAME(striptype));
        return NULL;
    }

    return do_strip(self, striptype);
}


PyDoc_STRVAR(strip__doc__,
"S.strip([chars]) -> string or unicode\n\
\n\
Return a copy of the string S with leading and trailing\n\
whitespace removed.\n\
If chars is given and not None, remove characters in chars instead.\n\
If chars is unicode, S will be converted to unicode before stripping");

static PyObject *
string_strip(PyStringObject *self, PyObject *args)
{
    if (PyTuple_GET_SIZE(args) == 0)
        return do_strip(self, BOTHSTRIP); /* Common case */
    else
        return do_argstrip(self, BOTHSTRIP, args);
}


PyDoc_STRVAR(lstrip__doc__,
"S.lstrip([chars]) -> string or unicode\n\
\n\
Return a copy of the string S with leading whitespace removed.\n\
If chars is given and not None, remove characters in chars instead.\n\
If chars is unicode, S will be converted to unicode before stripping");

static PyObject *
string_lstrip(PyStringObject *self, PyObject *args)
{
    if (PyTuple_GET_SIZE(args) == 0)
        return do_strip(self, LEFTSTRIP); /* Common case */
    else
        return do_argstrip(self, LEFTSTRIP, args);
}


PyDoc_STRVAR(rstrip__doc__,
"S.rstrip([chars]) -> string or unicode\n\
\n\
Return a copy of the string S with trailing whitespace removed.\n\
If chars is given and not None, remove characters in chars instead.\n\
If chars is unicode, S will be converted to unicode before stripping");

static PyObject *
string_rstrip(PyStringObject *self, PyObject *args)
{
    if (PyTuple_GET_SIZE(args) == 0)
        return do_strip(self, RIGHTSTRIP); /* Common case */
    else
        return do_argstrip(self, RIGHTSTRIP, args);
}


PyDoc_STRVAR(lower__doc__,
"S.lower() -> string\n\
\n\
Return a copy of the string S converted to lowercase.");

/* _tolower and _toupper are defined by SUSv2, but they're not ISO C */
#ifndef _tolower
#define _tolower tolower
#endif

static PyObject *
string_lower(PyStringObject *self)
{
    char *s;
    Py_ssize_t i, n = PyString_GET_SIZE(self);
    PyObject *newobj;

    newobj = PyString_FromStringAndSize(NULL, n);
    if (!newobj)
        return NULL;

    s = PyString_AS_STRING(newobj);

    Py_MEMCPY(s, PyString_AS_STRING(self), n);

    for (i = 0; i < n; i++) {
        int c = Py_CHARMASK(s[i]);
        if (isupper(c))
            s[i] = _tolower(c);
    }

    return newobj;
}

PyDoc_STRVAR(upper__doc__,
"S.upper() -> string\n\
\n\
Return a copy of the string S converted to uppercase.");

#ifndef _toupper
#define _toupper toupper
#endif

static PyObject *
string_upper(PyStringObject *self)
{
    char *s;
    Py_ssize_t i, n = PyString_GET_SIZE(self);
    PyObject *newobj;

    newobj = PyString_FromStringAndSize(NULL, n);
    if (!newobj)
        return NULL;

    s = PyString_AS_STRING(newobj);

    Py_MEMCPY(s, PyString_AS_STRING(self), n);

    for (i = 0; i < n; i++) {
        int c = Py_CHARMASK(s[i]);
        if (islower(c))
            s[i] = _toupper(c);
    }

    return newobj;
}

PyDoc_STRVAR(title__doc__,
"S.title() -> string\n\
\n\
Return a titlecased version of S, i.e. words start with uppercase\n\
characters, all remaining cased characters have lowercase.");

static PyObject*
string_title(PyStringObject *self)
{
    char *s = PyString_AS_STRING(self), *s_new;
    Py_ssize_t i, n = PyString_GET_SIZE(self);
    int previous_is_cased = 0;
    PyObject *newobj;

    newobj = PyString_FromStringAndSize(NULL, n);
    if (newobj == NULL)
        return NULL;
    s_new = PyString_AsString(newobj);
    for (i = 0; i < n; i++) {
        int c = Py_CHARMASK(*s++);
        if (islower(c)) {
            if (!previous_is_cased)
                c = toupper(c);
            previous_is_cased = 1;
        } else if (isupper(c)) {
            if (previous_is_cased)
                c = tolower(c);
            previous_is_cased = 1;
        } else
            previous_is_cased = 0;
        *s_new++ = c;
    }
    return newobj;
}

PyDoc_STRVAR(capitalize__doc__,
"S.capitalize() -> string\n\
\n\
Return a copy of the string S with only its first character\n\
capitalized.");

static PyObject *
string_capitalize(PyStringObject *self)
{
    char *s = PyString_AS_STRING(self), *s_new;
    Py_ssize_t i, n = PyString_GET_SIZE(self);
    PyObject *newobj;

    newobj = PyString_FromStringAndSize(NULL, n);
    if (newobj == NULL)
        return NULL;
    s_new = PyString_AsString(newobj);
    if (0 < n) {
        int c = Py_CHARMASK(*s++);
        if (islower(c))
            *s_new = toupper(c);
        else
            *s_new = c;
        s_new++;
    }
    for (i = 1; i < n; i++) {
        int c = Py_CHARMASK(*s++);
        if (isupper(c))
            *s_new = tolower(c);
        else
            *s_new = c;
        s_new++;
    }
    return newobj;
}


PyDoc_STRVAR(count__doc__,
"S.count(sub[, start[, end]]) -> int\n\
\n\
Return the number of non-overlapping occurrences of substring sub in\n\
string S[start:end].  Optional arguments start and end are interpreted\n\
as in slice notation.");

static PyObject *
string_count(PyStringObject *self, PyObject *args)
{
    PyObject *sub_obj;
    const char *str = PyString_AS_STRING(self), *sub;
    Py_ssize_t sub_len;
    Py_ssize_t start = 0, end = PY_SSIZE_T_MAX;

    if (!stringlib_parse_args_finds("count", args, &sub_obj, &start, &end))
        return NULL;

    if (PyString_Check(sub_obj)) {
        sub = PyString_AS_STRING(sub_obj);
        sub_len = PyString_GET_SIZE(sub_obj);
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(sub_obj)) {
        Py_ssize_t count;
        count = PyUnicode_Count((PyObject *)self, sub_obj, start, end);
        if (count == -1)
            return NULL;
        else
            return PyInt_FromSsize_t(count);
    }
#endif
    else if (PyObject_AsCharBuffer(sub_obj, &sub, &sub_len))
        return NULL;

    ADJUST_INDICES(start, end, PyString_GET_SIZE(self));

    return PyInt_FromSsize_t(
        stringlib_count(str + start, end - start, sub, sub_len, PY_SSIZE_T_MAX)
        );
}

PyDoc_STRVAR(swapcase__doc__,
"S.swapcase() -> string\n\
\n\
Return a copy of the string S with uppercase characters\n\
converted to lowercase and vice versa.");

static PyObject *
string_swapcase(PyStringObject *self)
{
    char *s = PyString_AS_STRING(self), *s_new;
    Py_ssize_t i, n = PyString_GET_SIZE(self);
    PyObject *newobj;

    newobj = PyString_FromStringAndSize(NULL, n);
    if (newobj == NULL)
        return NULL;
    s_new = PyString_AsString(newobj);
    for (i = 0; i < n; i++) {
        int c = Py_CHARMASK(*s++);
        if (islower(c)) {
            *s_new = toupper(c);
        }
        else if (isupper(c)) {
            *s_new = tolower(c);
        }
        else
            *s_new = c;
        s_new++;
    }
    return newobj;
}


PyDoc_STRVAR(translate__doc__,
"S.translate(table [,deletechars]) -> string\n\
\n\
Return a copy of the string S, where all characters occurring\n\
in the optional argument deletechars are removed, and the\n\
remaining characters have been mapped through the given\n\
translation table, which must be a string of length 256 or None.\n\
If the table argument is None, no translation is applied and\n\
the operation simply removes the characters in deletechars.");

static PyObject *
string_translate(PyStringObject *self, PyObject *args)
{
    register char *input, *output;
    const char *table;
    register Py_ssize_t i, c, changed = 0;
    PyObject *input_obj = (PyObject*)self;
    const char *output_start, *del_table=NULL;
    Py_ssize_t inlen, tablen, dellen = 0;
    PyObject *result;
    int trans_table[256];
    PyObject *tableobj, *delobj = NULL;

    if (!PyArg_UnpackTuple(args, "translate", 1, 2,
                          &tableobj, &delobj))
        return NULL;

    if (PyString_Check(tableobj)) {
        table = PyString_AS_STRING(tableobj);
        tablen = PyString_GET_SIZE(tableobj);
    }
    else if (tableobj == Py_None) {
        table = NULL;
        tablen = 256;
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(tableobj)) {
        /* Unicode .translate() does not support the deletechars
           parameter; instead a mapping to None will cause characters
           to be deleted. */
        if (delobj != NULL) {
            PyErr_SetString(PyExc_TypeError,
            "deletions are implemented differently for unicode");
            return NULL;
        }
        return PyUnicode_Translate((PyObject *)self, tableobj, NULL);
    }
#endif
    else if (PyObject_AsCharBuffer(tableobj, &table, &tablen))
        return NULL;

    if (tablen != 256) {
        PyErr_SetString(PyExc_ValueError,
          "translation table must be 256 characters long");
        return NULL;
    }

    if (delobj != NULL) {
        if (PyString_Check(delobj)) {
            del_table = PyString_AS_STRING(delobj);
            dellen = PyString_GET_SIZE(delobj);
        }
#ifdef Py_USING_UNICODE
        else if (PyUnicode_Check(delobj)) {
            PyErr_SetString(PyExc_TypeError,
            "deletions are implemented differently for unicode");
            return NULL;
        }
#endif
        else if (PyObject_AsCharBuffer(delobj, &del_table, &dellen))
            return NULL;
    }
    else {
        del_table = NULL;
        dellen = 0;
    }

    inlen = PyString_GET_SIZE(input_obj);
    result = PyString_FromStringAndSize((char *)NULL, inlen);
    if (result == NULL)
        return NULL;
    output_start = output = PyString_AsString(result);
    input = PyString_AS_STRING(input_obj);

    if (dellen == 0 && table != NULL) {
        /* If no deletions are required, use faster code */
        for (i = inlen; --i >= 0; ) {
            c = Py_CHARMASK(*input++);
            if (Py_CHARMASK((*output++ = table[c])) != c)
                changed = 1;
        }
        if (changed || !PyString_CheckExact(input_obj))
            return result;
        Py_DECREF(result);
        Py_INCREF(input_obj);
        return input_obj;
    }

    if (table == NULL) {
        for (i = 0; i < 256; i++)
            trans_table[i] = Py_CHARMASK(i);
    } else {
        for (i = 0; i < 256; i++)
            trans_table[i] = Py_CHARMASK(table[i]);
    }

    for (i = 0; i < dellen; i++)
        trans_table[(int) Py_CHARMASK(del_table[i])] = -1;

    for (i = inlen; --i >= 0; ) {
        c = Py_CHARMASK(*input++);
        if (trans_table[c] != -1)
            if (Py_CHARMASK(*output++ = (char)trans_table[c]) == c)
                continue;
        changed = 1;
    }
    if (!changed && PyString_CheckExact(input_obj)) {
        Py_DECREF(result);
        Py_INCREF(input_obj);
        return input_obj;
    }
    /* Fix the size of the resulting string */
    if (inlen > 0 && _PyString_Resize(&result, output - output_start))
        return NULL;
    return result;
}


/* find and count characters and substrings */

#define findchar(target, target_len, c)                         \
  ((char *)memchr((const void *)(target), c, target_len))

/* String ops must return a string.  */
/* If the object is subclass of string, create a copy */
Py_LOCAL(PyStringObject *)
return_self(PyStringObject *self)
{
    if (PyString_CheckExact(self)) {
        Py_INCREF(self);
        return self;
    }
    return (PyStringObject *)PyString_FromStringAndSize(
        PyString_AS_STRING(self),
        PyString_GET_SIZE(self));
}

Py_LOCAL_INLINE(Py_ssize_t)
countchar(const char *target, Py_ssize_t target_len, char c, Py_ssize_t maxcount)
{
    Py_ssize_t count=0;
    const char *start=target;
    const char *end=target+target_len;

    while ( (start=findchar(start, end-start, c)) != NULL ) {
        count++;
        if (count >= maxcount)
            break;
        start += 1;
    }
    return count;
}


/* Algorithms for different cases of string replacement */

/* len(self)>=1, from="", len(to)>=1, maxcount>=1 */
Py_LOCAL(PyStringObject *)
replace_interleave(PyStringObject *self,
                   const char *to_s, Py_ssize_t to_len,
                   Py_ssize_t maxcount)
{
    char *self_s, *result_s;
    Py_ssize_t self_len, result_len;
    Py_ssize_t count, i, product;
    PyStringObject *result;

    self_len = PyString_GET_SIZE(self);

    /* 1 at the end plus 1 after every character */
    count = self_len+1;
    if (maxcount < count)
        count = maxcount;

    /* Check for overflow */
    /*   result_len = count * to_len + self_len; */
    product = count * to_len;
    if (product / to_len != count) {
        PyErr_SetString(PyExc_OverflowError,
                        "replace string is too long");
        return NULL;
    }
    result_len = product + self_len;
    if (result_len < 0) {
        PyErr_SetString(PyExc_OverflowError,
                        "replace string is too long");
        return NULL;
    }

    if (! (result = (PyStringObject *)
                     PyString_FromStringAndSize(NULL, result_len)) )
        return NULL;

    self_s = PyString_AS_STRING(self);
    result_s = PyString_AS_STRING(result);

    /* TODO: special case single character, which doesn't need memcpy */

    /* Lay the first one down (guaranteed this will occur) */
    Py_MEMCPY(result_s, to_s, to_len);
    result_s += to_len;
    count -= 1;

    for (i=0; i<count; i++) {
        *result_s++ = *self_s++;
        Py_MEMCPY(result_s, to_s, to_len);
        result_s += to_len;
    }

    /* Copy the rest of the original string */
    Py_MEMCPY(result_s, self_s, self_len-i);

    return result;
}

/* Special case for deleting a single character */
/* len(self)>=1, len(from)==1, to="", maxcount>=1 */
Py_LOCAL(PyStringObject *)
replace_delete_single_character(PyStringObject *self,
                                char from_c, Py_ssize_t maxcount)
{
    char *self_s, *result_s;
    char *start, *next, *end;
    Py_ssize_t self_len, result_len;
    Py_ssize_t count;
    PyStringObject *result;

    self_len = PyString_GET_SIZE(self);
    self_s = PyString_AS_STRING(self);

    count = countchar(self_s, self_len, from_c, maxcount);
    if (count == 0) {
        return return_self(self);
    }

    result_len = self_len - count;  /* from_len == 1 */
    assert(result_len>=0);

    if ( (result = (PyStringObject *)
                    PyString_FromStringAndSize(NULL, result_len)) == NULL)
        return NULL;
    result_s = PyString_AS_STRING(result);

    start = self_s;
    end = self_s + self_len;
    while (count-- > 0) {
        next = findchar(start, end-start, from_c);
        if (next == NULL)
            break;
        Py_MEMCPY(result_s, start, next-start);
        result_s += (next-start);
        start = next+1;
    }
    Py_MEMCPY(result_s, start, end-start);

    return result;
}

/* len(self)>=1, len(from)>=2, to="", maxcount>=1 */

Py_LOCAL(PyStringObject *)
replace_delete_substring(PyStringObject *self,
                         const char *from_s, Py_ssize_t from_len,
                         Py_ssize_t maxcount) {
    char *self_s, *result_s;
    char *start, *next, *end;
    Py_ssize_t self_len, result_len;
    Py_ssize_t count, offset;
    PyStringObject *result;

    self_len = PyString_GET_SIZE(self);
    self_s = PyString_AS_STRING(self);

    count = stringlib_count(self_s, self_len,
                            from_s, from_len,
                            maxcount);

    if (count == 0) {
        /* no matches */
        return return_self(self);
    }

    result_len = self_len - (count * from_len);
    assert (result_len>=0);

    if ( (result = (PyStringObject *)
          PyString_FromStringAndSize(NULL, result_len)) == NULL )
        return NULL;

    result_s = PyString_AS_STRING(result);

    start = self_s;
    end = self_s + self_len;
    while (count-- > 0) {
        offset = stringlib_find(start, end-start,
                                from_s, from_len,
                                0);
        if (offset == -1)
            break;
        next = start + offset;

        Py_MEMCPY(result_s, start, next-start);

        result_s += (next-start);
        start = next+from_len;
    }
    Py_MEMCPY(result_s, start, end-start);
    return result;
}

/* len(self)>=1, len(from)==len(to)==1, maxcount>=1 */
Py_LOCAL(PyStringObject *)
replace_single_character_in_place(PyStringObject *self,
                                  char from_c, char to_c,
                                  Py_ssize_t maxcount)
{
    char *self_s, *result_s, *start, *end, *next;
    Py_ssize_t self_len;
    PyStringObject *result;

    /* The result string will be the same size */
    self_s = PyString_AS_STRING(self);
    self_len = PyString_GET_SIZE(self);

    next = findchar(self_s, self_len, from_c);

    if (next == NULL) {
        /* No matches; return the original string */
        return return_self(self);
    }

    /* Need to make a new string */
    result = (PyStringObject *) PyString_FromStringAndSize(NULL, self_len);
    if (result == NULL)
        return NULL;
    result_s = PyString_AS_STRING(result);
    Py_MEMCPY(result_s, self_s, self_len);

    /* change everything in-place, starting with this one */
    start =  result_s + (next-self_s);
    *start = to_c;
    start++;
    end = result_s + self_len;

    while (--maxcount > 0) {
        next = findchar(start, end-start, from_c);
        if (next == NULL)
            break;
        *next = to_c;
        start = next+1;
    }

    return result;
}

/* len(self)>=1, len(from)==len(to)>=2, maxcount>=1 */
Py_LOCAL(PyStringObject *)
replace_substring_in_place(PyStringObject *self,
                           const char *from_s, Py_ssize_t from_len,
                           const char *to_s, Py_ssize_t to_len,
                           Py_ssize_t maxcount)
{
    char *result_s, *start, *end;
    char *self_s;
    Py_ssize_t self_len, offset;
    PyStringObject *result;

    /* The result string will be the same size */

    self_s = PyString_AS_STRING(self);
    self_len = PyString_GET_SIZE(self);

    offset = stringlib_find(self_s, self_len,
                            from_s, from_len,
                            0);
    if (offset == -1) {
        /* No matches; return the original string */
        return return_self(self);
    }

    /* Need to make a new string */
    result = (PyStringObject *) PyString_FromStringAndSize(NULL, self_len);
    if (result == NULL)
        return NULL;
    result_s = PyString_AS_STRING(result);
    Py_MEMCPY(result_s, self_s, self_len);

    /* change everything in-place, starting with this one */
    start =  result_s + offset;
    Py_MEMCPY(start, to_s, from_len);
    start += from_len;
    end = result_s + self_len;

    while ( --maxcount > 0) {
        offset = stringlib_find(start, end-start,
                                from_s, from_len,
                                0);
        if (offset==-1)
            break;
        Py_MEMCPY(start+offset, to_s, from_len);
        start += offset+from_len;
    }

    return result;
}

/* len(self)>=1, len(from)==1, len(to)>=2, maxcount>=1 */
Py_LOCAL(PyStringObject *)
replace_single_character(PyStringObject *self,
                         char from_c,
                         const char *to_s, Py_ssize_t to_len,
                         Py_ssize_t maxcount)
{
    char *self_s, *result_s;
    char *start, *next, *end;
    Py_ssize_t self_len, result_len;
    Py_ssize_t count, product;
    PyStringObject *result;

    self_s = PyString_AS_STRING(self);
    self_len = PyString_GET_SIZE(self);

    count = countchar(self_s, self_len, from_c, maxcount);
    if (count == 0) {
        /* no matches, return unchanged */
        return return_self(self);
    }

    /* use the difference between current and new, hence the "-1" */
    /*   result_len = self_len + count * (to_len-1)  */
    product = count * (to_len-1);
    if (product / (to_len-1) != count) {
        PyErr_SetString(PyExc_OverflowError, "replace string is too long");
        return NULL;
    }
    result_len = self_len + product;
    if (result_len < 0) {
        PyErr_SetString(PyExc_OverflowError, "replace string is too long");
        return NULL;
    }

    if ( (result = (PyStringObject *)
          PyString_FromStringAndSize(NULL, result_len)) == NULL)
        return NULL;
    result_s = PyString_AS_STRING(result);

    start = self_s;
    end = self_s + self_len;
    while (count-- > 0) {
        next = findchar(start, end-start, from_c);
        if (next == NULL)
            break;

        if (next == start) {
            /* replace with the 'to' */
            Py_MEMCPY(result_s, to_s, to_len);
            result_s += to_len;
            start += 1;
        } else {
            /* copy the unchanged old then the 'to' */
            Py_MEMCPY(result_s, start, next-start);
            result_s += (next-start);
            Py_MEMCPY(result_s, to_s, to_len);
            result_s += to_len;
            start = next+1;
        }
    }
    /* Copy the remainder of the remaining string */
    Py_MEMCPY(result_s, start, end-start);

    return result;
}

/* len(self)>=1, len(from)>=2, len(to)>=2, maxcount>=1 */
Py_LOCAL(PyStringObject *)
replace_substring(PyStringObject *self,
                  const char *from_s, Py_ssize_t from_len,
                  const char *to_s, Py_ssize_t to_len,
                  Py_ssize_t maxcount) {
    char *self_s, *result_s;
    char *start, *next, *end;
    Py_ssize_t self_len, result_len;
    Py_ssize_t count, offset, product;
    PyStringObject *result;

    self_s = PyString_AS_STRING(self);
    self_len = PyString_GET_SIZE(self);

    count = stringlib_count(self_s, self_len,
                            from_s, from_len,
                            maxcount);

    if (count == 0) {
        /* no matches, return unchanged */
        return return_self(self);
    }

    /* Check for overflow */
    /*    result_len = self_len + count * (to_len-from_len) */
    product = count * (to_len-from_len);
    if (product / (to_len-from_len) != count) {
        PyErr_SetString(PyExc_OverflowError, "replace string is too long");
        return NULL;
    }
    result_len = self_len + product;
    if (result_len < 0) {
        PyErr_SetString(PyExc_OverflowError, "replace string is too long");
        return NULL;
    }

    if ( (result = (PyStringObject *)
          PyString_FromStringAndSize(NULL, result_len)) == NULL)
        return NULL;
    result_s = PyString_AS_STRING(result);

    start = self_s;
    end = self_s + self_len;
    while (count-- > 0) {
        offset = stringlib_find(start, end-start,
                                from_s, from_len,
                                0);
        if (offset == -1)
            break;
        next = start+offset;
        if (next == start) {
            /* replace with the 'to' */
            Py_MEMCPY(result_s, to_s, to_len);
            result_s += to_len;
            start += from_len;
        } else {
            /* copy the unchanged old then the 'to' */
            Py_MEMCPY(result_s, start, next-start);
            result_s += (next-start);
            Py_MEMCPY(result_s, to_s, to_len);
            result_s += to_len;
            start = next+from_len;
        }
    }
    /* Copy the remainder of the remaining string */
    Py_MEMCPY(result_s, start, end-start);

    return result;
}


Py_LOCAL(PyStringObject *)
replace(PyStringObject *self,
    const char *from_s, Py_ssize_t from_len,
    const char *to_s, Py_ssize_t to_len,
    Py_ssize_t maxcount)
{
    if (maxcount < 0) {
        maxcount = PY_SSIZE_T_MAX;
    } else if (maxcount == 0 || PyString_GET_SIZE(self) == 0) {
        /* nothing to do; return the original string */
        return return_self(self);
    }

    if (maxcount == 0 ||
        (from_len == 0 && to_len == 0)) {
        /* nothing to do; return the original string */
        return return_self(self);
    }

    /* Handle zero-length special cases */

    if (from_len == 0) {
        /* insert the 'to' string everywhere.   */
        /*    >>> "Python".replace("", ".")     */
        /*    '.P.y.t.h.o.n.'                   */
        return replace_interleave(self, to_s, to_len, maxcount);
    }

    /* Except for "".replace("", "A") == "A" there is no way beyond this */
    /* point for an empty self string to generate a non-empty string */
    /* Special case so the remaining code always gets a non-empty string */
    if (PyString_GET_SIZE(self) == 0) {
        return return_self(self);
    }

    if (to_len == 0) {
        /* delete all occurrences of 'from' string */
        if (from_len == 1) {
            return replace_delete_single_character(
                self, from_s[0], maxcount);
        } else {
            return replace_delete_substring(self, from_s, from_len, maxcount);
        }
    }

    /* Handle special case where both strings have the same length */

    if (from_len == to_len) {
        if (from_len == 1) {
            return replace_single_character_in_place(
                self,
                from_s[0],
                to_s[0],
                maxcount);
        } else {
            return replace_substring_in_place(
                self, from_s, from_len, to_s, to_len, maxcount);
        }
    }

    /* Otherwise use the more generic algorithms */
    if (from_len == 1) {
        return replace_single_character(self, from_s[0],
                                        to_s, to_len, maxcount);
    } else {
        /* len('from')>=2, len('to')>=1 */
        return replace_substring(self, from_s, from_len, to_s, to_len, maxcount);
    }
}

PyDoc_STRVAR(replace__doc__,
"S.replace(old, new[, count]) -> string\n\
\n\
Return a copy of string S with all occurrences of substring\n\
old replaced by new.  If the optional argument count is\n\
given, only the first count occurrences are replaced.");

static PyObject *
string_replace(PyStringObject *self, PyObject *args)
{
    Py_ssize_t count = -1;
    PyObject *from, *to;
    const char *from_s, *to_s;
    Py_ssize_t from_len, to_len;

    if (!PyArg_ParseTuple(args, "OO|n:replace", &from, &to, &count))
        return NULL;

    if (PyString_Check(from)) {
        from_s = PyString_AS_STRING(from);
        from_len = PyString_GET_SIZE(from);
    }
#ifdef Py_USING_UNICODE
    if (PyUnicode_Check(from))
        return PyUnicode_Replace((PyObject *)self,
                                 from, to, count);
#endif
    else if (PyObject_AsCharBuffer(from, &from_s, &from_len))
        return NULL;

    if (PyString_Check(to)) {
        to_s = PyString_AS_STRING(to);
        to_len = PyString_GET_SIZE(to);
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(to))
        return PyUnicode_Replace((PyObject *)self,
                                 from, to, count);
#endif
    else if (PyObject_AsCharBuffer(to, &to_s, &to_len))
        return NULL;

    return (PyObject *)replace((PyStringObject *) self,
                               from_s, from_len,
                               to_s, to_len, count);
}

/** End DALKE **/

/* Matches the end (direction >= 0) or start (direction < 0) of self
 * against substr, using the start and end arguments. Returns
 * -1 on error, 0 if not found and 1 if found.
 */
Py_LOCAL(int)
_string_tailmatch(PyStringObject *self, PyObject *substr, Py_ssize_t start,
                  Py_ssize_t end, int direction)
{
    Py_ssize_t len = PyString_GET_SIZE(self);
    Py_ssize_t slen;
    const char* sub;
    const char* str;

    if (PyString_Check(substr)) {
        sub = PyString_AS_STRING(substr);
        slen = PyString_GET_SIZE(substr);
    }
#ifdef Py_USING_UNICODE
    else if (PyUnicode_Check(substr))
        return PyUnicode_Tailmatch((PyObject *)self,
                                   substr, start, end, direction);
#endif
    else if (PyObject_AsCharBuffer(substr, &sub, &slen))
        return -1;
    str = PyString_AS_STRING(self);

    ADJUST_INDICES(start, end, len);

    if (direction < 0) {
        /* startswith */
        if (start+slen > len)
            return 0;
    } else {
        /* endswith */
        if (end-start < slen || start > len)
            return 0;

        if (end-slen > start)
            start = end - slen;
    }
    if (end-start >= slen)
        return ! memcmp(str+start, sub, slen);
    return 0;
}


PyDoc_STRVAR(startswith__doc__,
"S.startswith(prefix[, start[, end]]) -> bool\n\
\n\
Return True if S starts with the specified prefix, False otherwise.\n\
With optional start, test S beginning at that position.\n\
With optional end, stop comparing S at that position.\n\
prefix can also be a tuple of strings to try.");

static PyObject *
string_startswith(PyStringObject *self, PyObject *args)
{
    Py_ssize_t start = 0;
    Py_ssize_t end = PY_SSIZE_T_MAX;
    PyObject *subobj;
    int result;

    if (!stringlib_parse_args_finds("startswith", args, &subobj, &start, &end))
        return NULL;
    if (PyTuple_Check(subobj)) {
        Py_ssize_t i;
        for (i = 0; i < PyTuple_GET_SIZE(subobj); i++) {
            result = _string_tailmatch(self,
                            PyTuple_GET_ITEM(subobj, i),
                            start, end, -1);
            if (result == -1)
                return NULL;
            else if (result) {
                Py_RETURN_TRUE;
            }
        }
        Py_RETURN_FALSE;
    }
    result = _string_tailmatch(self, subobj, start, end, -1);
    if (result == -1) {
        if (PyErr_ExceptionMatches(PyExc_TypeError))
            PyErr_Format(PyExc_TypeError, "startswith first arg must be str, "
                         "unicode, or tuple, not %s", Py_TYPE(subobj)->tp_name);
        return NULL;
    }
    else
        return PyBool_FromLong(result);
}


PyDoc_STRVAR(endswith__doc__,
"S.endswith(suffix[, start[, end]]) -> bool\n\
\n\
Return True if S ends with the specified suffix, False otherwise.\n\
With optional start, test S beginning at that position.\n\
With optional end, stop comparing S at that position.\n\
suffix can also be a tuple of strings to try.");

static PyObject *
string_endswith(PyStringObject *self, PyObject *args)
{
    Py_ssize_t start = 0;
    Py_ssize_t end = PY_SSIZE_T_MAX;
    PyObject *subobj;
    int result;

    if (!stringlib_parse_args_finds("endswith", args, &subobj, &start, &end))
        return NULL;
    if (PyTuple_Check(subobj)) {
        Py_ssize_t i;
        for (i = 0; i < PyTuple_GET_SIZE(subobj); i++) {
            result = _string_tailmatch(self,
                            PyTuple_GET_ITEM(subobj, i),
                            start, end, +1);
            if (result == -1)
                return NULL;
            else if (result) {
                Py_RETURN_TRUE;
            }
        }
        Py_RETURN_FALSE;
    }
    result = _string_tailmatch(self, subobj, start, end, +1);
    if (result == -1) {
        if (PyErr_ExceptionMatches(PyExc_TypeError))
            PyErr_Format(PyExc_TypeError, "endswith first arg must be str, "
                         "unicode, or tuple, not %s", Py_TYPE(subobj)->tp_name);
        return NULL;
    }
    else
        return PyBool_FromLong(result);
}


#ifndef OVM_MAIN
PyDoc_STRVAR(encode__doc__,
"S.encode([encoding[,errors]]) -> object\n\
\n\
Encodes S using the codec registered for encoding. encoding defaults\n\
to the default encoding. errors may be given to set a different error\n\
handling scheme. Default is 'strict' meaning that encoding errors raise\n\
a UnicodeEncodeError. Other possible values are 'ignore', 'replace' and\n\
'xmlcharrefreplace' as well as any other name registered with\n\
codecs.register_error that is able to handle UnicodeEncodeErrors.");

static PyObject *
string_encode(PyStringObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"encoding", "errors", 0};
    char *encoding = NULL;
    char *errors = NULL;
    PyObject *v;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|ss:encode",
                                     kwlist, &encoding, &errors))
        return NULL;
    v = PyString_AsEncodedObject((PyObject *)self, encoding, errors);
    if (v == NULL)
        goto onError;
    if (!PyString_Check(v) && !PyUnicode_Check(v)) {
        PyErr_Format(PyExc_TypeError,
                     "encoder did not return a string/unicode object "
                     "(type=%.400s)",
                     Py_TYPE(v)->tp_name);
        Py_DECREF(v);
        return NULL;
    }
    return v;

 onError:
    return NULL;
}


PyDoc_STRVAR(decode__doc__,
"S.decode([encoding[,errors]]) -> object\n\
\n\
Decodes S using the codec registered for encoding. encoding defaults\n\
to the default encoding. errors may be given to set a different error\n\
handling scheme. Default is 'strict' meaning that encoding errors raise\n\
a UnicodeDecodeError. Other possible values are 'ignore' and 'replace'\n\
as well as any other name registered with codecs.register_error that is\n\
able to handle UnicodeDecodeErrors.");

static PyObject *
string_decode(PyStringObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"encoding", "errors", 0};
    char *encoding = NULL;
    char *errors = NULL;
    PyObject *v;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|ss:decode",
                                     kwlist, &encoding, &errors))
        return NULL;
    v = PyString_AsDecodedObject((PyObject *)self, encoding, errors);
    if (v == NULL)
        goto onError;
    if (!PyString_Check(v) && !PyUnicode_Check(v)) {
        PyErr_Format(PyExc_TypeError,
                     "decoder did not return a string/unicode object "
                     "(type=%.400s)",
                     Py_TYPE(v)->tp_name);
        Py_DECREF(v);
        return NULL;
    }
    return v;

 onError:
    return NULL;
}
#endif


PyDoc_STRVAR(expandtabs__doc__,
"S.expandtabs([tabsize]) -> string\n\
\n\
Return a copy of S where all tab characters are expanded using spaces.\n\
If tabsize is not given, a tab size of 8 characters is assumed.");

static PyObject*
string_expandtabs(PyStringObject *self, PyObject *args)
{
    const char *e, *p, *qe;
    char *q;
    Py_ssize_t i, j, incr;
    PyObject *u;
    int tabsize = 8;

    if (!PyArg_ParseTuple(args, "|i:expandtabs", &tabsize))
        return NULL;

    /* First pass: determine size of output string */
    i = 0; /* chars up to and including most recent \n or \r */
    j = 0; /* chars since most recent \n or \r (use in tab calculations) */
    e = PyString_AS_STRING(self) + PyString_GET_SIZE(self); /* end of input */
    for (p = PyString_AS_STRING(self); p < e; p++) {
        if (*p == '\t') {
            if (tabsize > 0) {
                incr = tabsize - (j % tabsize);
                if (j > PY_SSIZE_T_MAX - incr)
                    goto overflow1;
                j += incr;
            }
        }
        else {
            if (j > PY_SSIZE_T_MAX - 1)
                goto overflow1;
            j++;
            if (*p == '\n' || *p == '\r') {
                if (i > PY_SSIZE_T_MAX - j)
                    goto overflow1;
                i += j;
                j = 0;
            }
        }
    }

    if (i > PY_SSIZE_T_MAX - j)
        goto overflow1;

    /* Second pass: create output string and fill it */
    u = PyString_FromStringAndSize(NULL, i + j);
    if (!u)
        return NULL;

    j = 0; /* same as in first pass */
    q = PyString_AS_STRING(u); /* next output char */
    qe = PyString_AS_STRING(u) + PyString_GET_SIZE(u); /* end of output */

    for (p = PyString_AS_STRING(self); p < e; p++) {
        if (*p == '\t') {
            if (tabsize > 0) {
                i = tabsize - (j % tabsize);
                j += i;
                while (i--) {
                    if (q >= qe)
                        goto overflow2;
                    *q++ = ' ';
                }
            }
        }
        else {
            if (q >= qe)
                goto overflow2;
            *q++ = *p;
            j++;
            if (*p == '\n' || *p == '\r')
                j = 0;
        }
    }

    return u;

  overflow2:
    Py_DECREF(u);
  overflow1:
    PyErr_SetString(PyExc_OverflowError, "new string is too long");
    return NULL;
}

Py_LOCAL_INLINE(PyObject *)
pad(PyStringObject *self, Py_ssize_t left, Py_ssize_t right, char fill)
{
    PyObject *u;

    if (left < 0)
        left = 0;
    if (right < 0)
        right = 0;

    if (left == 0 && right == 0 && PyString_CheckExact(self)) {
        Py_INCREF(self);
        return (PyObject *)self;
    }

    u = PyString_FromStringAndSize(NULL,
                                   left + PyString_GET_SIZE(self) + right);
    if (u) {
        if (left)
            memset(PyString_AS_STRING(u), fill, left);
        Py_MEMCPY(PyString_AS_STRING(u) + left,
               PyString_AS_STRING(self),
               PyString_GET_SIZE(self));
        if (right)
            memset(PyString_AS_STRING(u) + left + PyString_GET_SIZE(self),
               fill, right);
    }

    return u;
}

PyDoc_STRVAR(ljust__doc__,
"S.ljust(width[, fillchar]) -> string\n"
"\n"
"Return S left-justified in a string of length width. Padding is\n"
"done using the specified fill character (default is a space).");

static PyObject *
string_ljust(PyStringObject *self, PyObject *args)
{
    Py_ssize_t width;
    char fillchar = ' ';

    if (!PyArg_ParseTuple(args, "n|c:ljust", &width, &fillchar))
        return NULL;

    if (PyString_GET_SIZE(self) >= width && PyString_CheckExact(self)) {
        Py_INCREF(self);
        return (PyObject*) self;
    }

    return pad(self, 0, width - PyString_GET_SIZE(self), fillchar);
}


PyDoc_STRVAR(rjust__doc__,
"S.rjust(width[, fillchar]) -> string\n"
"\n"
"Return S right-justified in a string of length width. Padding is\n"
"done using the specified fill character (default is a space)");

static PyObject *
string_rjust(PyStringObject *self, PyObject *args)
{
    Py_ssize_t width;
    char fillchar = ' ';

    if (!PyArg_ParseTuple(args, "n|c:rjust", &width, &fillchar))
        return NULL;

    if (PyString_GET_SIZE(self) >= width && PyString_CheckExact(self)) {
        Py_INCREF(self);
        return (PyObject*) self;
    }

    return pad(self, width - PyString_GET_SIZE(self), 0, fillchar);
}


PyDoc_STRVAR(center__doc__,
"S.center(width[, fillchar]) -> string\n"
"\n"
"Return S centered in a string of length width. Padding is\n"
"done using the specified fill character (default is a space)");

static PyObject *
string_center(PyStringObject *self, PyObject *args)
{
    Py_ssize_t marg, left;
    Py_ssize_t width;
    char fillchar = ' ';

    if (!PyArg_ParseTuple(args, "n|c:center", &width, &fillchar))
        return NULL;

    if (PyString_GET_SIZE(self) >= width && PyString_CheckExact(self)) {
        Py_INCREF(self);
        return (PyObject*) self;
    }

    marg = width - PyString_GET_SIZE(self);
    left = marg / 2 + (marg & width & 1);

    return pad(self, left, marg - left, fillchar);
}

PyDoc_STRVAR(zfill__doc__,
"S.zfill(width) -> string\n"
"\n"
"Pad a numeric string S with zeros on the left, to fill a field\n"
"of the specified width.  The string S is never truncated.");

static PyObject *
string_zfill(PyStringObject *self, PyObject *args)
{
    Py_ssize_t fill;
    PyObject *s;
    char *p;
    Py_ssize_t width;

    if (!PyArg_ParseTuple(args, "n:zfill", &width))
        return NULL;

    if (PyString_GET_SIZE(self) >= width) {
        if (PyString_CheckExact(self)) {
            Py_INCREF(self);
            return (PyObject*) self;
        }
        else
            return PyString_FromStringAndSize(
                PyString_AS_STRING(self),
                PyString_GET_SIZE(self)
            );
    }

    fill = width - PyString_GET_SIZE(self);

    s = pad(self, fill, 0, '0');

    if (s == NULL)
        return NULL;

    p = PyString_AS_STRING(s);
    if (p[fill] == '+' || p[fill] == '-') {
        /* move sign to beginning of string */
        p[0] = p[fill];
        p[fill] = '0';
    }

    return (PyObject*) s;
}

PyDoc_STRVAR(isspace__doc__,
"S.isspace() -> bool\n\
\n\
Return True if all characters in S are whitespace\n\
and there is at least one character in S, False otherwise.");

static PyObject*
string_isspace(PyStringObject *self)
{
    register const unsigned char *p
        = (unsigned char *) PyString_AS_STRING(self);
    register const unsigned char *e;

    /* Shortcut for single character strings */
    if (PyString_GET_SIZE(self) == 1 &&
        isspace(*p))
        return PyBool_FromLong(1);

    /* Special case for empty strings */
    if (PyString_GET_SIZE(self) == 0)
        return PyBool_FromLong(0);

    e = p + PyString_GET_SIZE(self);
    for (; p < e; p++) {
        if (!isspace(*p))
            return PyBool_FromLong(0);
    }
    return PyBool_FromLong(1);
}


PyDoc_STRVAR(isalpha__doc__,
"S.isalpha() -> bool\n\
\n\
Return True if all characters in S are alphabetic\n\
and there is at least one character in S, False otherwise.");

static PyObject*
string_isalpha(PyStringObject *self)
{
    register const unsigned char *p
        = (unsigned char *) PyString_AS_STRING(self);
    register const unsigned char *e;

    /* Shortcut for single character strings */
    if (PyString_GET_SIZE(self) == 1 &&
        isalpha(*p))
        return PyBool_FromLong(1);

    /* Special case for empty strings */
    if (PyString_GET_SIZE(self) == 0)
        return PyBool_FromLong(0);

    e = p + PyString_GET_SIZE(self);
    for (; p < e; p++) {
        if (!isalpha(*p))
            return PyBool_FromLong(0);
    }
    return PyBool_FromLong(1);
}


PyDoc_STRVAR(isalnum__doc__,
"S.isalnum() -> bool\n\
\n\
Return True if all characters in S are alphanumeric\n\
and there is at least one character in S, False otherwise.");

static PyObject*
string_isalnum(PyStringObject *self)
{
    register const unsigned char *p
        = (unsigned char *) PyString_AS_STRING(self);
    register const unsigned char *e;

    /* Shortcut for single character strings */
    if (PyString_GET_SIZE(self) == 1 &&
        isalnum(*p))
        return PyBool_FromLong(1);

    /* Special case for empty strings */
    if (PyString_GET_SIZE(self) == 0)
        return PyBool_FromLong(0);

    e = p + PyString_GET_SIZE(self);
    for (; p < e; p++) {
        if (!isalnum(*p))
            return PyBool_FromLong(0);
    }
    return PyBool_FromLong(1);
}


PyDoc_STRVAR(isdigit__doc__,
"S.isdigit() -> bool\n\
\n\
Return True if all characters in S are digits\n\
and there is at least one character in S, False otherwise.");

static PyObject*
string_isdigit(PyStringObject *self)
{
    register const unsigned char *p
        = (unsigned char *) PyString_AS_STRING(self);
    register const unsigned char *e;

    /* Shortcut for single character strings */
    if (PyString_GET_SIZE(self) == 1 &&
        isdigit(*p))
        return PyBool_FromLong(1);

    /* Special case for empty strings */
    if (PyString_GET_SIZE(self) == 0)
        return PyBool_FromLong(0);

    e = p + PyString_GET_SIZE(self);
    for (; p < e; p++) {
        if (!isdigit(*p))
            return PyBool_FromLong(0);
    }
    return PyBool_FromLong(1);
}


PyDoc_STRVAR(islower__doc__,
"S.islower() -> bool\n\
\n\
Return True if all cased characters in S are lowercase and there is\n\
at least one cased character in S, False otherwise.");

static PyObject*
string_islower(PyStringObject *self)
{
    register const unsigned char *p
        = (unsigned char *) PyString_AS_STRING(self);
    register const unsigned char *e;
    int cased;

    /* Shortcut for single character strings */
    if (PyString_GET_SIZE(self) == 1)
        return PyBool_FromLong(islower(*p) != 0);

    /* Special case for empty strings */
    if (PyString_GET_SIZE(self) == 0)
        return PyBool_FromLong(0);

    e = p + PyString_GET_SIZE(self);
    cased = 0;
    for (; p < e; p++) {
        if (isupper(*p))
            return PyBool_FromLong(0);
        else if (!cased && islower(*p))
            cased = 1;
    }
    return PyBool_FromLong(cased);
}


PyDoc_STRVAR(isupper__doc__,
"S.isupper() -> bool\n\
\n\
Return True if all cased characters in S are uppercase and there is\n\
at least one cased character in S, False otherwise.");

static PyObject*
string_isupper(PyStringObject *self)
{
    register const unsigned char *p
        = (unsigned char *) PyString_AS_STRING(self);
    register const unsigned char *e;
    int cased;

    /* Shortcut for single character strings */
    if (PyString_GET_SIZE(self) == 1)
        return PyBool_FromLong(isupper(*p) != 0);

    /* Special case for empty strings */
    if (PyString_GET_SIZE(self) == 0)
        return PyBool_FromLong(0);

    e = p + PyString_GET_SIZE(self);
    cased = 0;
    for (; p < e; p++) {
        if (islower(*p))
            return PyBool_FromLong(0);
        else if (!cased && isupper(*p))
            cased = 1;
    }
    return PyBool_FromLong(cased);
}


PyDoc_STRVAR(istitle__doc__,
"S.istitle() -> bool\n\
\n\
Return True if S is a titlecased string and there is at least one\n\
character in S, i.e. uppercase characters may only follow uncased\n\
characters and lowercase characters only cased ones. Return False\n\
otherwise.");

static PyObject*
string_istitle(PyStringObject *self, PyObject *uncased)
{
    register const unsigned char *p
        = (unsigned char *) PyString_AS_STRING(self);
    register const unsigned char *e;
    int cased, previous_is_cased;

    /* Shortcut for single character strings */
    if (PyString_GET_SIZE(self) == 1)
        return PyBool_FromLong(isupper(*p) != 0);

    /* Special case for empty strings */
    if (PyString_GET_SIZE(self) == 0)
        return PyBool_FromLong(0);

    e = p + PyString_GET_SIZE(self);
    cased = 0;
    previous_is_cased = 0;
    for (; p < e; p++) {
        register const unsigned char ch = *p;

        if (isupper(ch)) {
            if (previous_is_cased)
                return PyBool_FromLong(0);
            previous_is_cased = 1;
            cased = 1;
        }
        else if (islower(ch)) {
            if (!previous_is_cased)
                return PyBool_FromLong(0);
            previous_is_cased = 1;
            cased = 1;
        }
        else
            previous_is_cased = 0;
    }
    return PyBool_FromLong(cased);
}


PyDoc_STRVAR(splitlines__doc__,
"S.splitlines(keepends=False) -> list of strings\n\
\n\
Return a list of the lines in S, breaking at line boundaries.\n\
Line breaks are not included in the resulting list unless keepends\n\
is given and true.");

static PyObject*
string_splitlines(PyStringObject *self, PyObject *args)
{
    int keepends = 0;

    if (!PyArg_ParseTuple(args, "|i:splitlines", &keepends))
        return NULL;

    return stringlib_splitlines(
        (PyObject*) self, PyString_AS_STRING(self), PyString_GET_SIZE(self),
        keepends
    );
}

PyDoc_STRVAR(sizeof__doc__,
"S.__sizeof__() -> size of S in memory, in bytes");

static PyObject *
string_sizeof(PyStringObject *v)
{
    Py_ssize_t res;
    res = PyStringObject_SIZE + PyString_GET_SIZE(v) * Py_TYPE(v)->tp_itemsize;
    return PyInt_FromSsize_t(res);
}

static PyObject *
string_getnewargs(PyStringObject *v)
{
    return Py_BuildValue("(s#)", v->ob_sval, Py_SIZE(v));
}


#ifndef OVM_MAIN
#include "stringlib/string_format.h"

PyDoc_STRVAR(format__doc__,
"S.format(*args, **kwargs) -> string\n\
\n\
Return a formatted version of S, using substitutions from args and kwargs.\n\
The substitutions are identified by braces ('{' and '}').");

static PyObject *
string__format__(PyObject* self, PyObject* args)
{
    PyObject *format_spec;
    PyObject *result = NULL;
    PyObject *tmp = NULL;

    /* If 2.x, convert format_spec to the same type as value */
    /* This is to allow things like u''.format('') */
    if (!PyArg_ParseTuple(args, "O:__format__", &format_spec))
        goto done;
    if (!(PyString_Check(format_spec) || PyUnicode_Check(format_spec))) {
        PyErr_Format(PyExc_TypeError, "__format__ arg must be str "
                     "or unicode, not %s", Py_TYPE(format_spec)->tp_name);
        goto done;
    }
    tmp = PyObject_Str(format_spec);
    if (tmp == NULL)
        goto done;
    format_spec = tmp;

    result = _PyBytes_FormatAdvanced(self,
                                     PyString_AS_STRING(format_spec),
                                     PyString_GET_SIZE(format_spec));
done:
    Py_XDECREF(tmp);
    return result;
}

PyDoc_STRVAR(p_format__doc__,
"S.__format__(format_spec) -> string\n\
\n\
Return a formatted version of S as described by format_spec.");
#endif


static PyMethodDef string_methods[] = {
    /* Counterparts of the obsolete stropmodule functions; except
       string.maketrans(). */
    {"join", (PyCFunction)string_join, METH_O, join__doc__},
    {"split", (PyCFunction)string_split, METH_VARARGS, split__doc__},
    {"rsplit", (PyCFunction)string_rsplit, METH_VARARGS, rsplit__doc__},
    {"lower", (PyCFunction)string_lower, METH_NOARGS, lower__doc__},
    {"upper", (PyCFunction)string_upper, METH_NOARGS, upper__doc__},
    {"islower", (PyCFunction)string_islower, METH_NOARGS, islower__doc__},
    {"isupper", (PyCFunction)string_isupper, METH_NOARGS, isupper__doc__},
    {"isspace", (PyCFunction)string_isspace, METH_NOARGS, isspace__doc__},
    {"isdigit", (PyCFunction)string_isdigit, METH_NOARGS, isdigit__doc__},
    {"istitle", (PyCFunction)string_istitle, METH_NOARGS, istitle__doc__},
    {"isalpha", (PyCFunction)string_isalpha, METH_NOARGS, isalpha__doc__},
    {"isalnum", (PyCFunction)string_isalnum, METH_NOARGS, isalnum__doc__},
    {"capitalize", (PyCFunction)string_capitalize, METH_NOARGS,
     capitalize__doc__},
    {"count", (PyCFunction)string_count, METH_VARARGS, count__doc__},
    {"endswith", (PyCFunction)string_endswith, METH_VARARGS,
     endswith__doc__},
    {"partition", (PyCFunction)string_partition, METH_O, partition__doc__},
    {"find", (PyCFunction)string_find, METH_VARARGS, find__doc__},
    {"index", (PyCFunction)string_index, METH_VARARGS, index__doc__},
    {"lstrip", (PyCFunction)string_lstrip, METH_VARARGS, lstrip__doc__},
    {"replace", (PyCFunction)string_replace, METH_VARARGS, replace__doc__},
    {"rfind", (PyCFunction)string_rfind, METH_VARARGS, rfind__doc__},
    {"rindex", (PyCFunction)string_rindex, METH_VARARGS, rindex__doc__},
    {"rstrip", (PyCFunction)string_rstrip, METH_VARARGS, rstrip__doc__},
    {"rpartition", (PyCFunction)string_rpartition, METH_O,
     rpartition__doc__},
    {"startswith", (PyCFunction)string_startswith, METH_VARARGS,
     startswith__doc__},
    {"strip", (PyCFunction)string_strip, METH_VARARGS, strip__doc__},
    {"swapcase", (PyCFunction)string_swapcase, METH_NOARGS,
     swapcase__doc__},
    {"translate", (PyCFunction)string_translate, METH_VARARGS,
     translate__doc__},
    {"title", (PyCFunction)string_title, METH_NOARGS, title__doc__},
    {"ljust", (PyCFunction)string_ljust, METH_VARARGS, ljust__doc__},
    {"rjust", (PyCFunction)string_rjust, METH_VARARGS, rjust__doc__},
    {"center", (PyCFunction)string_center, METH_VARARGS, center__doc__},
    {"zfill", (PyCFunction)string_zfill, METH_VARARGS, zfill__doc__},
#ifndef OVM_MAIN
    {"format", (PyCFunction) do_string_format, METH_VARARGS | METH_KEYWORDS, format__doc__},
    {"__format__", (PyCFunction) string__format__, METH_VARARGS, p_format__doc__},
    {"_formatter_field_name_split", (PyCFunction) formatter_field_name_split, METH_NOARGS},
    {"_formatter_parser", (PyCFunction) formatter_parser, METH_NOARGS},
#endif
#ifndef OVM_MAIN
    {"encode", (PyCFunction)string_encode, METH_VARARGS | METH_KEYWORDS, encode__doc__},
    {"decode", (PyCFunction)string_decode, METH_VARARGS | METH_KEYWORDS, decode__doc__},
#endif
    {"expandtabs", (PyCFunction)string_expandtabs, METH_VARARGS,
     expandtabs__doc__},
    {"splitlines", (PyCFunction)string_splitlines, METH_VARARGS,
     splitlines__doc__},
    {"__sizeof__", (PyCFunction)string_sizeof, METH_NOARGS,
     sizeof__doc__},
    {"__getnewargs__",          (PyCFunction)string_getnewargs, METH_NOARGS},
    {NULL,     NULL}                         /* sentinel */
};

static PyObject *
str_subtype_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static PyObject *
string_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyObject *x = NULL;
    static char *kwlist[] = {"object", 0};

    if (type != &PyString_Type)
        return str_subtype_new(type, args, kwds);
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O:str", kwlist, &x))
        return NULL;
    if (x == NULL)
        return PyString_FromString("");
    return PyObject_Str(x);
}

static PyObject *
str_subtype_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyObject *tmp, *pnew;
    Py_ssize_t n;

    assert(PyType_IsSubtype(type, &PyString_Type));
    tmp = string_new(&PyString_Type, args, kwds);
    if (tmp == NULL)
        return NULL;
    assert(PyString_Check(tmp));
    n = PyString_GET_SIZE(tmp);
    pnew = type->tp_alloc(type, n);
    if (pnew != NULL) {
        Py_MEMCPY(PyString_AS_STRING(pnew), PyString_AS_STRING(tmp), n+1);
        ((PyStringObject *)pnew)->ob_shash =
            ((PyStringObject *)tmp)->ob_shash;
        ((PyStringObject *)pnew)->ob_sstate = SSTATE_NOT_INTERNED;
    }
    Py_DECREF(tmp);
    return pnew;
}

static PyObject *
basestring_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyErr_SetString(PyExc_TypeError,
                    "The basestring type cannot be instantiated");
    return NULL;
}

static PyObject *
string_mod(PyObject *v, PyObject *w)
{
    if (!PyString_Check(v)) {
        Py_INCREF(Py_NotImplemented);
        return Py_NotImplemented;
    }
    return PyString_Format(v, w);
}

PyDoc_STRVAR(basestring_doc,
"Type basestring cannot be instantiated; it is the base for str and unicode.");

static PyNumberMethods string_as_number = {
    0,                          /*nb_add*/
    0,                          /*nb_subtract*/
    0,                          /*nb_multiply*/
    0,                          /*nb_divide*/
    string_mod,                 /*nb_remainder*/
};


PyTypeObject PyBaseString_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "basestring",
    0,
    0,
    0,                                          /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_compare */
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
    basestring_doc,                             /* tp_doc */
    0,                                          /* tp_traverse */
    0,                                          /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    0,                                          /* tp_methods */
    0,                                          /* tp_members */
    0,                                          /* tp_getset */
    &PyBaseObject_Type,                         /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    0,                                          /* tp_init */
    0,                                          /* tp_alloc */
    basestring_new,                             /* tp_new */
    0,                                          /* tp_free */
};

PyDoc_STRVAR(string_doc,
"str(object='') -> string\n\
\n\
Return a nice string representation of the object.\n\
If the argument is a string, the return value is the same object.");

PyTypeObject PyString_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "str",
    PyStringObject_SIZE,
    sizeof(char),
    string_dealloc,                             /* tp_dealloc */
    (printfunc)string_print,                    /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_compare */
    string_repr,                                /* tp_repr */
    &string_as_number,                          /* tp_as_number */
    &string_as_sequence,                        /* tp_as_sequence */
    &string_as_mapping,                         /* tp_as_mapping */
    (hashfunc)string_hash,                      /* tp_hash */
    0,                                          /* tp_call */
    string_str,                                 /* tp_str */
    PyObject_GenericGetAttr,                    /* tp_getattro */
    0,                                          /* tp_setattro */
    &string_as_buffer,                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_CHECKTYPES |
        Py_TPFLAGS_BASETYPE | Py_TPFLAGS_STRING_SUBCLASS |
        Py_TPFLAGS_HAVE_NEWBUFFER,              /* tp_flags */
    string_doc,                                 /* tp_doc */
    0,                                          /* tp_traverse */
    0,                                          /* tp_clear */
    (richcmpfunc)string_richcompare,            /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    string_methods,                             /* tp_methods */
    0,                                          /* tp_members */
    0,                                          /* tp_getset */
    &PyBaseString_Type,                         /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    0,                                          /* tp_init */
    0,                                          /* tp_alloc */
    string_new,                                 /* tp_new */
    PyObject_Del,                               /* tp_free */
};

void
PyString_Concat(register PyObject **pv, register PyObject *w)
{
    register PyObject *v;
    if (*pv == NULL)
        return;
    if (w == NULL || !PyString_Check(*pv)) {
        Py_CLEAR(*pv);
        return;
    }
    v = string_concat((PyStringObject *) *pv, w);
    Py_SETREF(*pv, v);
}

void
PyString_ConcatAndDel(register PyObject **pv, register PyObject *w)
{
    PyString_Concat(pv, w);
    Py_XDECREF(w);
}


/* The following function breaks the notion that strings are immutable:
   it changes the size of a string.  We get away with this only if there
   is only one module referencing the object.  You can also think of it
   as creating a new string object and destroying the old one, only
   more efficiently.  In any case, don't use this if the string may
   already be known to some other part of the code...
   Note that if there's not enough memory to resize the string, the original
   string object at *pv is deallocated, *pv is set to NULL, an "out of
   memory" exception is set, and -1 is returned.  Else (on success) 0 is
   returned, and the value in *pv may or may not be the same as on input.
   As always, an extra byte is allocated for a trailing \0 byte (newsize
   does *not* include that), and a trailing \0 byte is stored.
*/

int
_PyString_Resize(PyObject **pv, Py_ssize_t newsize)
{
    register PyObject *v;
    register PyStringObject *sv;
    v = *pv;
    if (!PyString_Check(v) || Py_REFCNT(v) != 1 || newsize < 0 ||
        PyString_CHECK_INTERNED(v)) {
        *pv = 0;
        Py_DECREF(v);
        PyErr_BadInternalCall();
        return -1;
    }
    /* XXX UNREF/NEWREF interface should be more symmetrical */
    _Py_DEC_REFTOTAL;
    _Py_ForgetReference(v);
    *pv = (PyObject *)
        PyObject_REALLOC((char *)v, PyStringObject_SIZE + newsize);
    if (*pv == NULL) {
        PyObject_Del(v);
        PyErr_NoMemory();
        return -1;
    }
    _Py_NewReference(*pv);
    sv = (PyStringObject *) *pv;
    Py_SIZE(sv) = newsize;
    sv->ob_sval[newsize] = '\0';
    sv->ob_shash = -1;          /* invalidate cached hash value */
    return 0;
}

/* Helpers for formatstring */

Py_LOCAL_INLINE(PyObject *)
getnextarg(PyObject *args, Py_ssize_t arglen, Py_ssize_t *p_argidx)
{
    Py_ssize_t argidx = *p_argidx;
    if (argidx < arglen) {
        (*p_argidx)++;
        if (arglen < 0)
            return args;
        else
            return PyTuple_GetItem(args, argidx);
    }
    PyErr_SetString(PyExc_TypeError,
                    "not enough arguments for format string");
    return NULL;
}

/* Format codes
 * F_LJUST      '-'
 * F_SIGN       '+'
 * F_BLANK      ' '
 * F_ALT        '#'
 * F_ZERO       '0'
 */
#define F_LJUST (1<<0)
#define F_SIGN  (1<<1)
#define F_BLANK (1<<2)
#define F_ALT   (1<<3)
#define F_ZERO  (1<<4)

/* Returns a new reference to a PyString object, or NULL on failure. */

static PyObject *
formatfloat(PyObject *v, int flags, int prec, int type)
{
    char *p;
    PyObject *result;
    double x;

    x = PyFloat_AsDouble(v);
    if (x == -1.0 && PyErr_Occurred()) {
        PyErr_Format(PyExc_TypeError, "float argument required, "
                     "not %.200s", Py_TYPE(v)->tp_name);
        return NULL;
    }

    if (prec < 0)
        prec = 6;

    p = PyOS_double_to_string(x, type, prec,
                              (flags & F_ALT) ? Py_DTSF_ALT : 0, NULL);

    if (p == NULL)
        return NULL;
    result = PyString_FromStringAndSize(p, strlen(p));
    PyMem_Free(p);
    return result;
}

/* _PyString_FormatLong emulates the format codes d, u, o, x and X, and
 * the F_ALT flag, for Python's long (unbounded) ints.  It's not used for
 * Python's regular ints.
 * Return value:  a new PyString*, or NULL if error.
 *  .  *pbuf is set to point into it,
 *     *plen set to the # of chars following that.
 *     Caller must decref it when done using pbuf.
 *     The string starting at *pbuf is of the form
 *         "-"? ("0x" | "0X")? digit+
 *     "0x"/"0X" are present only for x and X conversions, with F_ALT
 *         set in flags.  The case of hex digits will be correct,
 *     There will be at least prec digits, zero-filled on the left if
 *         necessary to get that many.
 * val          object to be converted
 * flags        bitmask of format flags; only F_ALT is looked at
 * prec         minimum number of digits; 0-fill on left if needed
 * type         a character in [duoxX]; u acts the same as d
 *
 * CAUTION:  o, x and X conversions on regular ints can never
 * produce a '-' sign, but can for Python's unbounded ints.
 */
PyObject*
_PyString_FormatLong(PyObject *val, int flags, int prec, int type,
                     char **pbuf, int *plen)
{
    PyObject *result = NULL, *r1;
    const char *s;
    char *buf;
    Py_ssize_t i;
    int sign;           /* 1 if '-', else 0 */
    int len;            /* number of characters */
    Py_ssize_t llen;
    int numdigits;      /* len == numnondigits + skipped + numdigits */
    int numnondigits, skipped, filled;
    const char *method;

    switch (type) {
    case 'd':
    case 'u':
        method = "str";
        result = Py_TYPE(val)->tp_str(val);
        break;
    case 'o':
        method = "oct";
        result = Py_TYPE(val)->tp_as_number->nb_oct(val);
        break;
    case 'x':
    case 'X':
        method = "hex";
        result = Py_TYPE(val)->tp_as_number->nb_hex(val);
        break;
    default:
        assert(!"'type' not in [duoxX]");
    }
    if (!result)
        return NULL;

    if (PyString_AsStringAndSize(result, (char **)&s, &llen) < 0) {
        Py_DECREF(result);
        return NULL;
    }
    if (llen > INT_MAX) {
        PyErr_SetString(PyExc_ValueError, "string too large in _PyString_FormatLong");
        Py_DECREF(result);
        return NULL;
    }
    len = (int)llen;
    if (len > 0 && s[len-1] == 'L') {
        --len;
        if (len == 0)
            goto error;
    }
    sign = s[0] == '-';
    numnondigits = sign;

    /* Need to skip 0x, 0X or 0. */
    skipped = 0;
    switch (type) {
    case 'o':
        if (s[sign] != '0')
            goto error;
        /* If 0 is only digit, leave it alone. */
        if ((flags & F_ALT) == 0 && len - sign > 1)
            skipped = 1;
        break;
    case 'x':
    case 'X':
        if (s[sign] != '0' || (s[sign + 1] != 'x' && s[sign + 1] != 'X'))
            goto error;
        if ((flags & F_ALT) == 0)
            skipped = 2;
        else
            numnondigits += 2;
        break;
    }
    numdigits = len - numnondigits - skipped;
    if (numdigits <= 0)
        goto error;

    filled = prec - numdigits;
    if (filled < 0)
        filled = 0;
    len = numnondigits + filled + numdigits;

    /* To modify the string in-place, there can only be one reference. */
    if (skipped >= filled &&
        PyString_CheckExact(result) &&
        Py_REFCNT(result) == 1 &&
        !PyString_CHECK_INTERNED(result))
    {
        r1 = NULL;
        buf = (char *)s + skipped - filled;
    }
    else {
        r1 = result;
        result = PyString_FromStringAndSize(NULL, len);
        if (!result) {
            Py_DECREF(r1);
            return NULL;
        }
        buf = PyString_AS_STRING(result);
    }

    for (i = numnondigits; --i >= 0;)
        buf[i] = s[i];
    buf += numnondigits;
    s += numnondigits + skipped;
    for (i = 0; i < filled; i++)
        *buf++ = '0';
    if (r1 == NULL) {
        assert(buf == s);
        buf += numdigits;
    }
    else {
        for (i = 0; i < numdigits; i++)
            *buf++ = *s++;
    }
    *buf = '\0';
    buf -= len;
    Py_XDECREF(r1);

    /* Fix up case for hex conversions. */
    if (type == 'X') {
        /* Need to convert all lower case letters to upper case.
           and need to convert 0x to 0X (and -0x to -0X). */
        for (i = 0; i < len; i++) {
            if (buf[i] >= 'a' && buf[i] <= 'z')
                buf[i] -= 'a'-'A';
        }
    }
    *pbuf = buf;
    *plen = len;
    return result;

error:
    PyErr_Format(PyExc_ValueError,
                 "%%%c format: invalid result of __%s__ (type=%.200s)",
                 type, method, Py_TYPE(val)->tp_name);
    Py_DECREF(result);
    return NULL;
}

Py_LOCAL_INLINE(int)
formatint(char *buf, size_t buflen, int flags,
          int prec, int type, PyObject *v)
{
    /* fmt = '%#.' + `prec` + 'l' + `type`
       worst case length = 3 + 19 (worst len of INT_MAX on 64-bit machine)
       + 1 + 1 = 24 */
    char fmt[64];       /* plenty big enough! */
    char *sign;
    long x;

    x = PyInt_AsLong(v);
    if (x == -1 && PyErr_Occurred()) {
        PyErr_Format(PyExc_TypeError, "int argument required, not %.200s",
                     Py_TYPE(v)->tp_name);
        return -1;
    }
    if (x < 0 && type == 'u') {
        type = 'd';
    }
    if (x < 0 && (type == 'x' || type == 'X' || type == 'o'))
        sign = "-";
    else
        sign = "";
    if (prec < 0)
        prec = 1;

    if ((flags & F_ALT) &&
        (type == 'x' || type == 'X')) {
        /* When converting under %#x or %#X, there are a number
         * of issues that cause pain:
         * - when 0 is being converted, the C standard leaves off
         *   the '0x' or '0X', which is inconsistent with other
         *   %#x/%#X conversions and inconsistent with Python's
         *   hex() function
         * - there are platforms that violate the standard and
         *   convert 0 with the '0x' or '0X'
         *   (Metrowerks, Compaq Tru64)
         * - there are platforms that give '0x' when converting
         *   under %#X, but convert 0 in accordance with the
         *   standard (OS/2 EMX)
         *
         * We can achieve the desired consistency by inserting our
         * own '0x' or '0X' prefix, and substituting %x/%X in place
         * of %#x/%#X.
         *
         * Note that this is the same approach as used in
         * formatint() in unicodeobject.c
         */
        PyOS_snprintf(fmt, sizeof(fmt), "%s0%c%%.%dl%c",
                      sign, type, prec, type);
    }
    else {
        PyOS_snprintf(fmt, sizeof(fmt), "%s%%%s.%dl%c",
                      sign, (flags&F_ALT) ? "#" : "",
                      prec, type);
    }

    /* buf = '+'/'-'/'' + '0'/'0x'/'' + '[0-9]'*max(prec, len(x in octal))
     * worst case buf = '-0x' + [0-9]*prec, where prec >= 11
     */
    if (buflen <= 14 || buflen <= (size_t)3 + (size_t)prec) {
        PyErr_SetString(PyExc_OverflowError,
            "formatted integer is too long (precision too large?)");
        return -1;
    }
    if (sign[0])
        PyOS_snprintf(buf, buflen, fmt, -x);
    else
        PyOS_snprintf(buf, buflen, fmt, x);
    return (int)strlen(buf);
}

Py_LOCAL_INLINE(int)
formatchar(char *buf, size_t buflen, PyObject *v)
{
    /* presume that the buffer is at least 2 characters long */
    if (PyString_Check(v)) {
        if (!PyArg_Parse(v, "c;%c requires int or char", &buf[0]))
            return -1;
    }
    else {
        if (!PyArg_Parse(v, "b;%c requires int or char", &buf[0]))
            return -1;
    }
    buf[1] = '\0';
    return 1;
}

/* fmt%(v1,v2,...) is roughly equivalent to sprintf(fmt, v1, v2, ...)

   FORMATBUFLEN is the length of the buffer in which the ints &
   chars are formatted. XXX This is a magic number. Each formatting
   routine does bounds checking to ensure no overflow, but a better
   solution may be to malloc a buffer of appropriate size for each
   format. For now, the current solution is sufficient.
*/
#define FORMATBUFLEN (size_t)120

PyObject *
PyString_Format(PyObject *format, PyObject *args)
{
    char *fmt, *res;
    Py_ssize_t arglen, argidx;
    Py_ssize_t reslen, rescnt, fmtcnt;
    int args_owned = 0;
    PyObject *result;
#ifdef Py_USING_UNICODE
    PyObject *orig_args;
    PyObject *v, *w;
#endif
    PyObject *dict = NULL;
    if (format == NULL || !PyString_Check(format) || args == NULL) {
        PyErr_BadInternalCall();
        return NULL;
    }
#ifdef Py_USING_UNICODE
    orig_args = args;
#endif
    fmt = PyString_AS_STRING(format);
    fmtcnt = PyString_GET_SIZE(format);
    reslen = rescnt = fmtcnt + 100;
    result = PyString_FromStringAndSize((char *)NULL, reslen);
    if (result == NULL)
        return NULL;
    res = PyString_AsString(result);
    if (PyTuple_Check(args)) {
        arglen = PyTuple_GET_SIZE(args);
        argidx = 0;
    }
    else {
        arglen = -1;
        argidx = -2;
    }
    if (Py_TYPE(args)->tp_as_mapping && Py_TYPE(args)->tp_as_mapping->mp_subscript &&
        !PyTuple_Check(args) && !PyObject_TypeCheck(args, &PyBaseString_Type))
        dict = args;
    while (--fmtcnt >= 0) {
        if (*fmt != '%') {
            if (--rescnt < 0) {
                rescnt = fmtcnt + 100;
                reslen += rescnt;
                if (_PyString_Resize(&result, reslen))
                    return NULL;
                res = PyString_AS_STRING(result)
                    + reslen - rescnt;
                --rescnt;
            }
            *res++ = *fmt++;
        }
        else {
            /* Got a format specifier */
            int flags = 0;
            Py_ssize_t width = -1;
            int prec = -1;
            int c = '\0';
            int fill;
            int isnumok;
            PyObject *v = NULL;
            PyObject *temp = NULL;
            char *pbuf;
            int sign;
            Py_ssize_t len;
            char formatbuf[FORMATBUFLEN];
                 /* For format{int,char}() */
#ifdef Py_USING_UNICODE
            char *fmt_start = fmt;
            Py_ssize_t argidx_start = argidx;
#endif

            fmt++;
            if (*fmt == '(') {
                char *keystart;
                Py_ssize_t keylen;
                PyObject *key;
                int pcount = 1;

                if (dict == NULL) {
                    PyErr_SetString(PyExc_TypeError,
                             "format requires a mapping");
                    goto error;
                }
                ++fmt;
                --fmtcnt;
                keystart = fmt;
                /* Skip over balanced parentheses */
                while (pcount > 0 && --fmtcnt >= 0) {
                    if (*fmt == ')')
                        --pcount;
                    else if (*fmt == '(')
                        ++pcount;
                    fmt++;
                }
                keylen = fmt - keystart - 1;
                if (fmtcnt < 0 || pcount > 0) {
                    PyErr_SetString(PyExc_ValueError,
                               "incomplete format key");
                    goto error;
                }
                key = PyString_FromStringAndSize(keystart,
                                                 keylen);
                if (key == NULL)
                    goto error;
                if (args_owned) {
                    Py_DECREF(args);
                    args_owned = 0;
                }
                args = PyObject_GetItem(dict, key);
                Py_DECREF(key);
                if (args == NULL) {
                    goto error;
                }
                args_owned = 1;
                arglen = -1;
                argidx = -2;
            }
            while (--fmtcnt >= 0) {
                switch (c = *fmt++) {
                case '-': flags |= F_LJUST; continue;
                case '+': flags |= F_SIGN; continue;
                case ' ': flags |= F_BLANK; continue;
                case '#': flags |= F_ALT; continue;
                case '0': flags |= F_ZERO; continue;
                }
                break;
            }
            if (c == '*') {
                v = getnextarg(args, arglen, &argidx);
                if (v == NULL)
                    goto error;
                if (!PyInt_Check(v)) {
                    PyErr_SetString(PyExc_TypeError,
                                    "* wants int");
                    goto error;
                }
                width = PyInt_AsSsize_t(v);
                if (width == -1 && PyErr_Occurred())
                    goto error;
                if (width < 0) {
                    flags |= F_LJUST;
                    width = -width;
                }
                if (--fmtcnt >= 0)
                    c = *fmt++;
            }
            else if (c >= 0 && isdigit(c)) {
                width = c - '0';
                while (--fmtcnt >= 0) {
                    c = Py_CHARMASK(*fmt++);
                    if (!isdigit(c))
                        break;
                    if (width > (PY_SSIZE_T_MAX - ((int)c - '0')) / 10) {
                        PyErr_SetString(
                            PyExc_ValueError,
                            "width too big");
                        goto error;
                    }
                    width = width*10 + (c - '0');
                }
            }
            if (c == '.') {
                prec = 0;
                if (--fmtcnt >= 0)
                    c = *fmt++;
                if (c == '*') {
                    v = getnextarg(args, arglen, &argidx);
                    if (v == NULL)
                        goto error;
                    if (!PyInt_Check(v)) {
                        PyErr_SetString(
                            PyExc_TypeError,
                            "* wants int");
                        goto error;
                    }
                    prec = _PyInt_AsInt(v);
                    if (prec == -1 && PyErr_Occurred())
                        goto error;
                    if (prec < 0)
                        prec = 0;
                    if (--fmtcnt >= 0)
                        c = *fmt++;
                }
                else if (c >= 0 && isdigit(c)) {
                    prec = c - '0';
                    while (--fmtcnt >= 0) {
                        c = Py_CHARMASK(*fmt++);
                        if (!isdigit(c))
                            break;
                        if (prec > (INT_MAX - ((int)c - '0')) / 10) {
                            PyErr_SetString(
                                PyExc_ValueError,
                                "prec too big");
                            goto error;
                        }
                        prec = prec*10 + (c - '0');
                    }
                }
            } /* prec */
            if (fmtcnt >= 0) {
                if (c == 'h' || c == 'l' || c == 'L') {
                    if (--fmtcnt >= 0)
                        c = *fmt++;
                }
            }
            if (fmtcnt < 0) {
                PyErr_SetString(PyExc_ValueError,
                                "incomplete format");
                goto error;
            }
            if (c != '%') {
                v = getnextarg(args, arglen, &argidx);
                if (v == NULL)
                    goto error;
            }
            sign = 0;
            fill = ' ';
            switch (c) {
            case '%':
                pbuf = "%";
                len = 1;
                break;
            case 's':
#ifdef Py_USING_UNICODE
                if (PyUnicode_Check(v)) {
                    fmt = fmt_start;
                    argidx = argidx_start;
                    goto unicode;
                }
#endif
                temp = _PyObject_Str(v);
#ifdef Py_USING_UNICODE
                if (temp != NULL && PyUnicode_Check(temp)) {
                    Py_DECREF(temp);
                    fmt = fmt_start;
                    argidx = argidx_start;
                    goto unicode;
                }
#endif
                /* Fall through */
            case 'r':
                if (c == 'r')
                    temp = PyObject_Repr(v);
                if (temp == NULL)
                    goto error;
                if (!PyString_Check(temp)) {
                    PyErr_SetString(PyExc_TypeError,
                      "%s argument has non-string str()");
                    Py_DECREF(temp);
                    goto error;
                }
                pbuf = PyString_AS_STRING(temp);
                len = PyString_GET_SIZE(temp);
                if (prec >= 0 && len > prec)
                    len = prec;
                break;
            case 'i':
            case 'd':
            case 'u':
            case 'o':
            case 'x':
            case 'X':
                if (c == 'i')
                    c = 'd';
                isnumok = 0;
                if (PyNumber_Check(v)) {
                    PyObject *iobj=NULL;

                    if (PyInt_Check(v) || (PyLong_Check(v))) {
                        iobj = v;
                        Py_INCREF(iobj);
                    }
                    else {
                        iobj = PyNumber_Int(v);
                        if (iobj==NULL) {
                            PyErr_Clear();
                            iobj = PyNumber_Long(v);
                        }
                    }
                    if (iobj!=NULL) {
                        if (PyInt_Check(iobj)) {
                            isnumok = 1;
                            pbuf = formatbuf;
                            len = formatint(pbuf,
                                            sizeof(formatbuf),
                                            flags, prec, c, iobj);
                            Py_DECREF(iobj);
                            if (len < 0)
                                goto error;
                            sign = 1;
                        }
                        else if (PyLong_Check(iobj)) {
                            int ilen;

                            isnumok = 1;
                            temp = _PyString_FormatLong(iobj, flags,
                                prec, c, &pbuf, &ilen);
                            Py_DECREF(iobj);
                            len = ilen;
                            if (!temp)
                                goto error;
                            sign = 1;
                        }
                        else {
                            Py_DECREF(iobj);
                        }
                    }
                }
                if (!isnumok) {
                    PyErr_Format(PyExc_TypeError,
                        "%%%c format: a number is required, "
                        "not %.200s", c, Py_TYPE(v)->tp_name);
                    goto error;
                }
                if (flags & F_ZERO)
                    fill = '0';
                break;
            case 'e':
            case 'E':
            case 'f':
            case 'F':
            case 'g':
            case 'G':
                temp = formatfloat(v, flags, prec, c);
                if (temp == NULL)
                    goto error;
                pbuf = PyString_AS_STRING(temp);
                len = PyString_GET_SIZE(temp);
                sign = 1;
                if (flags & F_ZERO)
                    fill = '0';
                break;
            case 'c':
#ifdef Py_USING_UNICODE
                if (PyUnicode_Check(v)) {
                    fmt = fmt_start;
                    argidx = argidx_start;
                    goto unicode;
                }
#endif
                pbuf = formatbuf;
                len = formatchar(pbuf, sizeof(formatbuf), v);
                if (len < 0)
                    goto error;
                break;
            default:
                PyErr_Format(PyExc_ValueError,
                  "unsupported format character '%c' (0x%x) "
                  "at index %zd",
                  c, c,
                  (Py_ssize_t)(fmt - 1 -
                               PyString_AsString(format)));
                goto error;
            }
            if (sign) {
                if (*pbuf == '-' || *pbuf == '+') {
                    sign = *pbuf++;
                    len--;
                }
                else if (flags & F_SIGN)
                    sign = '+';
                else if (flags & F_BLANK)
                    sign = ' ';
                else
                    sign = 0;
            }
            if (width < len)
                width = len;
            if (rescnt - (sign != 0) < width) {
                reslen -= rescnt;
                rescnt = width + fmtcnt + 100;
                reslen += rescnt;
                if (reslen < 0) {
                    Py_DECREF(result);
                    Py_XDECREF(temp);
                    return PyErr_NoMemory();
                }
                if (_PyString_Resize(&result, reslen)) {
                    Py_XDECREF(temp);
                    return NULL;
                }
                res = PyString_AS_STRING(result)
                    + reslen - rescnt;
            }
            if (sign) {
                if (fill != ' ')
                    *res++ = sign;
                rescnt--;
                if (width > len)
                    width--;
            }
            if ((flags & F_ALT) && (c == 'x' || c == 'X')) {
                assert(pbuf[0] == '0');
                assert(pbuf[1] == c);
                if (fill != ' ') {
                    *res++ = *pbuf++;
                    *res++ = *pbuf++;
                }
                rescnt -= 2;
                width -= 2;
                if (width < 0)
                    width = 0;
                len -= 2;
            }
            if (width > len && !(flags & F_LJUST)) {
                do {
                    --rescnt;
                    *res++ = fill;
                } while (--width > len);
            }
            if (fill == ' ') {
                if (sign)
                    *res++ = sign;
                if ((flags & F_ALT) &&
                    (c == 'x' || c == 'X')) {
                    assert(pbuf[0] == '0');
                    assert(pbuf[1] == c);
                    *res++ = *pbuf++;
                    *res++ = *pbuf++;
                }
            }
            Py_MEMCPY(res, pbuf, len);
            res += len;
            rescnt -= len;
            while (--width >= len) {
                --rescnt;
                *res++ = ' ';
            }
            if (dict && (argidx < arglen) && c != '%') {
                PyErr_SetString(PyExc_TypeError,
                           "not all arguments converted during string formatting");
                Py_XDECREF(temp);
                goto error;
            }
            Py_XDECREF(temp);
        } /* '%' */
    } /* until end */
    if (argidx < arglen && !dict) {
        PyErr_SetString(PyExc_TypeError,
                        "not all arguments converted during string formatting");
        goto error;
    }
    if (args_owned) {
        Py_DECREF(args);
    }
    if (_PyString_Resize(&result, reslen - rescnt))
        return NULL;
    return result;

#ifdef Py_USING_UNICODE
 unicode:
    if (args_owned) {
        Py_DECREF(args);
        args_owned = 0;
    }
    /* Fiddle args right (remove the first argidx arguments) */
    if (PyTuple_Check(orig_args) && argidx > 0) {
        PyObject *v;
        Py_ssize_t n = PyTuple_GET_SIZE(orig_args) - argidx;
        v = PyTuple_New(n);
        if (v == NULL)
            goto error;
        while (--n >= 0) {
            PyObject *w = PyTuple_GET_ITEM(orig_args, n + argidx);
            Py_INCREF(w);
            PyTuple_SET_ITEM(v, n, w);
        }
        args = v;
    } else {
        Py_INCREF(orig_args);
        args = orig_args;
    }
    args_owned = 1;
    /* Take what we have of the result and let the Unicode formatting
       function format the rest of the input. */
    rescnt = res - PyString_AS_STRING(result);
    if (_PyString_Resize(&result, rescnt))
        goto error;
    fmtcnt = PyString_GET_SIZE(format) - \
             (fmt - PyString_AS_STRING(format));
    format = PyUnicode_Decode(fmt, fmtcnt, NULL, NULL);
    if (format == NULL)
        goto error;
    v = PyUnicode_Format(format, args);
    Py_DECREF(format);
    if (v == NULL)
        goto error;
    /* Paste what we have (result) to what the Unicode formatting
       function returned (v) and return the result (or error) */
    w = PyUnicode_Concat(result, v);
    Py_DECREF(result);
    Py_DECREF(v);
    Py_DECREF(args);
    return w;
#endif /* Py_USING_UNICODE */

 error:
    Py_DECREF(result);
    if (args_owned) {
        Py_DECREF(args);
    }
    return NULL;
}

void
PyString_InternInPlace(PyObject **p)
{
    register PyStringObject *s = (PyStringObject *)(*p);
    PyObject *t;
    if (s == NULL || !PyString_Check(s))
        Py_FatalError("PyString_InternInPlace: strings only please!");
    /* If it's a string subclass, we don't really know what putting
       it in the interned dict might do. */
    if (!PyString_CheckExact(s))
        return;
    if (PyString_CHECK_INTERNED(s))
        return;
    if (interned == NULL) {
        interned = PyDict_New();
        if (interned == NULL) {
            PyErr_Clear(); /* Don't leave an exception */
            return;
        }
    }
    t = PyDict_GetItem(interned, (PyObject *)s);
    if (t) {
        Py_INCREF(t);
        Py_SETREF(*p, t);
        return;
    }

    if (PyDict_SetItem(interned, (PyObject *)s, (PyObject *)s) < 0) {
        PyErr_Clear();
        return;
    }
    /* The two references in interned are not counted by refcnt.
       The string deallocator will take care of this */
    Py_REFCNT(s) -= 2;
    PyString_CHECK_INTERNED(s) = SSTATE_INTERNED_MORTAL;
}

void
PyString_InternImmortal(PyObject **p)
{
    PyString_InternInPlace(p);
    if (PyString_CHECK_INTERNED(*p) != SSTATE_INTERNED_IMMORTAL) {
        PyString_CHECK_INTERNED(*p) = SSTATE_INTERNED_IMMORTAL;
        Py_INCREF(*p);
    }
}


PyObject *
PyString_InternFromString(const char *cp)
{
    PyObject *s = PyString_FromString(cp);
    if (s == NULL)
        return NULL;
    PyString_InternInPlace(&s);
    return s;
}

void
PyString_Fini(void)
{
    int i;
    for (i = 0; i < UCHAR_MAX + 1; i++)
        Py_CLEAR(characters[i]);
    Py_CLEAR(nullstring);
}

void _Py_ReleaseInternedStrings(void)
{
    PyObject *keys;
    PyStringObject *s;
    Py_ssize_t i, n;
    Py_ssize_t immortal_size = 0, mortal_size = 0;

    if (interned == NULL || !PyDict_Check(interned))
        return;
    keys = PyDict_Keys(interned);
    if (keys == NULL || !PyList_Check(keys)) {
        PyErr_Clear();
        return;
    }

    /* Since _Py_ReleaseInternedStrings() is intended to help a leak
       detector, interned strings are not forcibly deallocated; rather, we
       give them their stolen references back, and then clear and DECREF
       the interned dict. */

    n = PyList_GET_SIZE(keys);
    fprintf(stderr, "releasing %" PY_FORMAT_SIZE_T "d interned strings\n",
        n);
    for (i = 0; i < n; i++) {
        s = (PyStringObject *) PyList_GET_ITEM(keys, i);
        switch (s->ob_sstate) {
        case SSTATE_NOT_INTERNED:
            /* XXX Shouldn't happen */
            break;
        case SSTATE_INTERNED_IMMORTAL:
            Py_REFCNT(s) += 1;
            immortal_size += Py_SIZE(s);
            break;
        case SSTATE_INTERNED_MORTAL:
            Py_REFCNT(s) += 2;
            mortal_size += Py_SIZE(s);
            break;
        default:
            Py_FatalError("Inconsistent interned string state.");
        }
        s->ob_sstate = SSTATE_NOT_INTERNED;
    }
    fprintf(stderr, "total size of all interned strings: "
                    "%" PY_FORMAT_SIZE_T "d/%" PY_FORMAT_SIZE_T "d "
                    "mortal/immortal\n", mortal_size, immortal_size);
    Py_DECREF(keys);
    PyDict_Clear(interned);
    Py_CLEAR(interned);
}

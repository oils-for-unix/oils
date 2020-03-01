
/* OVM_MAIN: POSIX module implementation stripped down for Oil */

#define PY_SSIZE_T_CLEAN

#include "Python.h"
#include "structseq.h"

#ifdef __cplusplus
extern "C" {
#endif

/* OVM_MAIN: For getting unused variable warnings while still keeping
 * "comments" */

#define PyDoc_STRVAR_remove(name,str)

PyDoc_STRVAR(posix__doc__,
"This module provides access to operating system functionality that is\n\
standardized by the C Standard and the POSIX standard (a thinly\n\
disguised Unix interface).  Refer to the library manual and\n\
corresponding Unix manual entries for more information on calls.");

/* OVM_MAIN: Turning off Unicode in build/setup_posix.py didn't work.
 *
 * If we don't turn it off we get build errors.
 * */
#undef Py_USING_UNICODE

#ifndef Py_USING_UNICODE
/* This is used in signatures of functions. */
#define Py_UNICODE void
#endif

#ifdef HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif /* HAVE_SYS_TYPES_H */

#ifdef HAVE_SYS_STAT_H
#include <sys/stat.h>
#endif /* HAVE_SYS_STAT_H */

#ifdef HAVE_SYS_WAIT_H
#include <sys/wait.h>           /* For WNOHANG */
#endif

#ifdef HAVE_SIGNAL_H
#include <signal.h>
#endif

#ifdef HAVE_FCNTL_H
#include <fcntl.h>
#endif /* HAVE_FCNTL_H */

/* sys/resource.h is needed for at least: wait3(), wait4(), broken nice. */
#if defined(HAVE_SYS_RESOURCE_H)
#include <sys/resource.h>
#endif

/* Unix functions that the configure script doesn't check for */
#define HAVE_EXECV      1
#define HAVE_FORK       1
#define HAVE_GETCWD     1
#define HAVE_GETEGID    1
#define HAVE_GETEUID    1
#define HAVE_GETGID     1
#define HAVE_GETPPID    1
#define HAVE_GETUID     1
#define HAVE_KILL       1
#define HAVE_PIPE       1
#define HAVE_WAIT       1

#ifndef HAVE_UNISTD_H
extern int mkdir(const char *, mode_t);
extern int chdir(const char *);
extern int rmdir(const char *);
extern int chmod(const char *, mode_t);
extern int chown(const char *, uid_t, gid_t);
extern char *getcwd(char *, int);
extern char *strerror(int);
extern int link(const char *, const char *);
extern int rename(const char *, const char *);
extern int stat(const char *, struct stat *);
extern int unlink(const char *);
extern int pclose(FILE *);
#ifdef HAVE_SYMLINK
extern int symlink(const char *, const char *);
#endif /* HAVE_SYMLINK */
#ifdef HAVE_LSTAT
extern int lstat(const char *, struct stat *);
#endif /* HAVE_LSTAT */
#endif /* !HAVE_UNISTD_H */

#ifdef HAVE_UTIME_H
#include <utime.h>
#endif /* HAVE_UTIME_H */

#ifdef HAVE_SYS_UTIME_H
#include <sys/utime.h>
#define HAVE_UTIME_H /* pretend we do for the rest of this file */
#endif /* HAVE_SYS_UTIME_H */

#ifdef HAVE_SYS_TIMES_H
#include <sys/times.h>
#endif /* HAVE_SYS_TIMES_H */

#ifdef HAVE_SYS_PARAM_H
#include <sys/param.h>
#endif /* HAVE_SYS_PARAM_H */

#ifdef HAVE_SYS_UTSNAME_H
#include <sys/utsname.h>
#endif /* HAVE_SYS_UTSNAME_H */

#ifdef HAVE_DIRENT_H
#include <dirent.h>
#define NAMLEN(dirent) strlen((dirent)->d_name)
#else
#if defined(__WATCOMC__) && !defined(__QNX__)
#include <direct.h>
#define NAMLEN(dirent) strlen((dirent)->d_name)
#else
#define dirent direct
#define NAMLEN(dirent) (dirent)->d_namlen
#endif
#ifdef HAVE_SYS_NDIR_H
#include <sys/ndir.h>
#endif
#ifdef HAVE_SYS_DIR_H
#include <sys/dir.h>
#endif
#ifdef HAVE_NDIR_H
#include <ndir.h>
#endif
#endif

#ifndef MAXPATHLEN
#if defined(PATH_MAX) && PATH_MAX > 1024
#define MAXPATHLEN PATH_MAX
#else
#define MAXPATHLEN 1024
#endif
#endif /* MAXPATHLEN */

#define WAIT_TYPE int
#define WAIT_STATUS_INT(s) (s)

/* Issue #1983: pid_t can be longer than a C long on some systems */
#if !defined(SIZEOF_PID_T) || SIZEOF_PID_T == SIZEOF_INT
#define PARSE_PID "i"
#define PyLong_FromPid PyInt_FromLong
#define PyLong_AsPid PyInt_AsLong
#elif SIZEOF_PID_T == SIZEOF_LONG
#define PARSE_PID "l"
#define PyLong_FromPid PyInt_FromLong
#define PyLong_AsPid PyInt_AsLong
#elif defined(SIZEOF_LONG_LONG) && SIZEOF_PID_T == SIZEOF_LONG_LONG
#define PARSE_PID "L"
#define PyLong_FromPid PyLong_FromLongLong
#define PyLong_AsPid PyInt_AsLongLong
#else
#error "sizeof(pid_t) is neither sizeof(int), sizeof(long) or sizeof(long long)"
#endif /* SIZEOF_PID_T */

/* Don't use the "_r" form if we don't need it (also, won't have a
   prototype for it, at least on Solaris -- maybe others as well?). */
#if defined(HAVE_CTERMID_R) && defined(WITH_THREAD)
#define USE_CTERMID_R
#endif

#if defined(HAVE_TMPNAM_R) && defined(WITH_THREAD)
#define USE_TMPNAM_R
#endif

#if defined(MAJOR_IN_MKDEV)
#include <sys/mkdev.h>
#else
#if defined(MAJOR_IN_SYSMACROS)
#include <sys/sysmacros.h>
#endif
#if defined(HAVE_MKNOD) && defined(HAVE_SYS_MKDEV_H)
#include <sys/mkdev.h>
#endif
#endif


PyObject *
_PyInt_FromUid(uid_t uid)
{
    if (uid <= LONG_MAX)
        return PyInt_FromLong(uid);
    return PyLong_FromUnsignedLong(uid);
}

PyObject *
_PyInt_FromGid(gid_t gid)
{
    if (gid <= LONG_MAX)
        return PyInt_FromLong(gid);
    return PyLong_FromUnsignedLong(gid);
}

int
_Py_Uid_Converter(PyObject *obj, void *p)
{
    int overflow;
    long result;
    if (PyFloat_Check(obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "integer argument expected, got float");
        return 0;
    }
    result = PyLong_AsLongAndOverflow(obj, &overflow);
    if (overflow < 0)
        goto OverflowDown;
    if (!overflow && result == -1) {
        /* error or -1 */
        if (PyErr_Occurred())
            return 0;
        *(uid_t *)p = (uid_t)-1;
    }
    else {
        /* unsigned uid_t */
        unsigned long uresult;
        if (overflow > 0) {
            uresult = PyLong_AsUnsignedLong(obj);
            if (PyErr_Occurred()) {
                if (PyErr_ExceptionMatches(PyExc_OverflowError))
                    goto OverflowUp;
                return 0;
            }
        } else {
            if (result < 0)
                goto OverflowDown;
            uresult = result;
        }
        if (sizeof(uid_t) < sizeof(long) &&
            (unsigned long)(uid_t)uresult != uresult)
            goto OverflowUp;
        *(uid_t *)p = (uid_t)uresult;
    }
    return 1;

OverflowDown:
    PyErr_SetString(PyExc_OverflowError,
                    "user id is less than minimum");
    return 0;

OverflowUp:
    PyErr_SetString(PyExc_OverflowError,
                    "user id is greater than maximum");
    return 0;
}

int
_Py_Gid_Converter(PyObject *obj, void *p)
{
    int overflow;
    long result;
    if (PyFloat_Check(obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "integer argument expected, got float");
        return 0;
    }
    result = PyLong_AsLongAndOverflow(obj, &overflow);
    if (overflow < 0)
        goto OverflowDown;
    if (!overflow && result == -1) {
        /* error or -1 */
        if (PyErr_Occurred())
            return 0;
        *(gid_t *)p = (gid_t)-1;
    }
    else {
        /* unsigned gid_t */
        unsigned long uresult;
        if (overflow > 0) {
            uresult = PyLong_AsUnsignedLong(obj);
            if (PyErr_Occurred()) {
                if (PyErr_ExceptionMatches(PyExc_OverflowError))
                    goto OverflowUp;
                return 0;
            }
        } else {
            if (result < 0)
                goto OverflowDown;
            uresult = result;
        }
        if (sizeof(gid_t) < sizeof(long) &&
            (unsigned long)(gid_t)uresult != uresult)
            goto OverflowUp;
        *(gid_t *)p = (gid_t)uresult;
    }
    return 1;

OverflowDown:
    PyErr_SetString(PyExc_OverflowError,
                    "group id is less than minimum");
    return 0;

OverflowUp:
    PyErr_SetString(PyExc_OverflowError,
                    "group id is greater than maximum");
    return 0;
}


#ifdef HAVE_LONG_LONG
static PyObject *
_PyInt_FromDev(PY_LONG_LONG v)
{
    if (LONG_MIN <= v && v <= LONG_MAX)
        return PyInt_FromLong((long)v);
    else
        return PyLong_FromLongLong(v);
}
#else
#  define _PyInt_FromDev PyInt_FromLong
#endif

#if defined(WITH_NEXT_FRAMEWORK) || (defined(__APPLE__) && defined(Py_ENABLE_SHARED))
/* On Darwin/MacOSX a shared library or framework has no access to
** environ directly, we must obtain it with _NSGetEnviron(). See also
** man environ(7).
*/
#include <crt_externs.h>
static char **environ;
#elif !defined(_MSC_VER) && ( !defined(__WATCOMC__) || defined(__QNX__) )
extern char **environ;
#endif /* !_MSC_VER */

static PyObject *
convertenviron(void)
{
    PyObject *d;
    char **e;
    d = PyDict_New();
    if (d == NULL)
        return NULL;
#if defined(WITH_NEXT_FRAMEWORK) || (defined(__APPLE__) && defined(Py_ENABLE_SHARED))
    if (environ == NULL)
        environ = *_NSGetEnviron();
#endif
    if (environ == NULL)
        return d;
    /* This part ignores errors */
    for (e = environ; *e != NULL; e++) {
        PyObject *k;
        PyObject *v;
        char *p = strchr(*e, '=');
        if (p == NULL)
            continue;
        k = PyString_FromStringAndSize(*e, (int)(p-*e));
        if (k == NULL) {
            PyErr_Clear();
            continue;
        }
        v = PyString_FromString(p+1);
        if (v == NULL) {
            PyErr_Clear();
            Py_DECREF(k);
            continue;
        }
        if (PyDict_GetItem(d, k) == NULL) {
            if (PyDict_SetItem(d, k, v) != 0)
                PyErr_Clear();
        }
        Py_DECREF(k);
        Py_DECREF(v);
    }
    return d;
}


/* Set a POSIX-specific error from errno, and return NULL */

static PyObject *
posix_error(void)
{
    return PyErr_SetFromErrno(PyExc_OSError);
}
static PyObject *
posix_error_with_filename(char* name)
{
    return PyErr_SetFromErrnoWithFilename(PyExc_OSError, name);
}

static PyObject *
posix_error_with_allocated_filename(char* name)
{
    PyObject *rc = PyErr_SetFromErrnoWithFilename(PyExc_OSError, name);
    PyMem_Free(name);
    return rc;
}

/* POSIX generic methods */

static PyObject *
posix_1str(PyObject *args, char *format, int (*func)(const char*))
{
    char *path1 = NULL;
    int res;
    if (!PyArg_ParseTuple(args, format,
                          Py_FileSystemDefaultEncoding, &path1))
        return NULL;
    Py_BEGIN_ALLOW_THREADS
    res = (*func)(path1);
    Py_END_ALLOW_THREADS
    if (res < 0)
        return posix_error_with_allocated_filename(path1);
    PyMem_Free(path1);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
posix_2str(PyObject *args,
           char *format,
           int (*func)(const char *, const char *))
{
    char *path1 = NULL, *path2 = NULL;
    int res;
    if (!PyArg_ParseTuple(args, format,
                          Py_FileSystemDefaultEncoding, &path1,
                          Py_FileSystemDefaultEncoding, &path2))
        return NULL;
    Py_BEGIN_ALLOW_THREADS
    res = (*func)(path1, path2);
    Py_END_ALLOW_THREADS
    PyMem_Free(path1);
    PyMem_Free(path2);
    if (res != 0)
        /* XXX how to report both path1 and path2??? */
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}

/* choose the appropriate stat and fstat functions and return structs */
#       define STAT stat
#       define FSTAT fstat
#       define STRUCT_STAT struct stat

PyDoc_STRVAR(stat_result__doc__,
"stat_result: Result from stat or lstat.\n\n\
This object may be accessed either as a tuple of\n\
  (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime)\n\
or via the attributes st_mode, st_ino, st_dev, st_nlink, st_uid, and so on.\n\
\n\
Posix/windows: If your platform supports st_blksize, st_blocks, st_rdev,\n\
or st_flags, they are available as attributes only.\n\
\n\
See os.stat for more information.");

static PyStructSequence_Field stat_result_fields[] = {
    {"st_mode",    "protection bits"},
    {"st_ino",     "inode"},
    {"st_dev",     "device"},
    {"st_nlink",   "number of hard links"},
    {"st_uid",     "user ID of owner"},
    {"st_gid",     "group ID of owner"},
    {"st_size",    "total size, in bytes"},
    /* The NULL is replaced with PyStructSequence_UnnamedField later. */
    {NULL,   "integer time of last access"},
    {NULL,   "integer time of last modification"},
    {NULL,   "integer time of last change"},
    {"st_atime",   "time of last access"},
    {"st_mtime",   "time of last modification"},
    {"st_ctime",   "time of last change"},
#ifdef HAVE_STRUCT_STAT_ST_BLKSIZE
    {"st_blksize", "blocksize for filesystem I/O"},
#endif
#ifdef HAVE_STRUCT_STAT_ST_BLOCKS
    {"st_blocks",  "number of blocks allocated"},
#endif
#ifdef HAVE_STRUCT_STAT_ST_RDEV
    {"st_rdev",    "device type (if inode device)"},
#endif
#ifdef HAVE_STRUCT_STAT_ST_FLAGS
    {"st_flags",   "user defined flags for file"},
#endif
#ifdef HAVE_STRUCT_STAT_ST_GEN
    {"st_gen",    "generation number"},
#endif
#ifdef HAVE_STRUCT_STAT_ST_BIRTHTIME
    {"st_birthtime",   "time of creation"},
#endif
    {0}
};

#ifdef HAVE_STRUCT_STAT_ST_BLKSIZE
#define ST_BLKSIZE_IDX 13
#else
#define ST_BLKSIZE_IDX 12
#endif

#ifdef HAVE_STRUCT_STAT_ST_BLOCKS
#define ST_BLOCKS_IDX (ST_BLKSIZE_IDX+1)
#else
#define ST_BLOCKS_IDX ST_BLKSIZE_IDX
#endif

#ifdef HAVE_STRUCT_STAT_ST_RDEV
#define ST_RDEV_IDX (ST_BLOCKS_IDX+1)
#else
#define ST_RDEV_IDX ST_BLOCKS_IDX
#endif

#ifdef HAVE_STRUCT_STAT_ST_FLAGS
#define ST_FLAGS_IDX (ST_RDEV_IDX+1)
#else
#define ST_FLAGS_IDX ST_RDEV_IDX
#endif

#ifdef HAVE_STRUCT_STAT_ST_GEN
#define ST_GEN_IDX (ST_FLAGS_IDX+1)
#else
#define ST_GEN_IDX ST_FLAGS_IDX
#endif

#ifdef HAVE_STRUCT_STAT_ST_BIRTHTIME
#define ST_BIRTHTIME_IDX (ST_GEN_IDX+1)
#else
#define ST_BIRTHTIME_IDX ST_GEN_IDX
#endif

static PyStructSequence_Desc stat_result_desc = {
    "stat_result", /* name */
    stat_result__doc__, /* doc */
    stat_result_fields,
    10
};

static int initialized;
static PyTypeObject StatResultType;
static newfunc structseq_new;

static PyObject *
statresult_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyStructSequence *result;
    int i;

    result = (PyStructSequence*)structseq_new(type, args, kwds);
    if (!result)
        return NULL;
    /* If we have been initialized from a tuple,
       st_?time might be set to None. Initialize it
       from the int slots.  */
    for (i = 7; i <= 9; i++) {
        if (result->ob_item[i+3] == Py_None) {
            Py_DECREF(Py_None);
            Py_INCREF(result->ob_item[i]);
            result->ob_item[i+3] = result->ob_item[i];
        }
    }
    return (PyObject*)result;
}



/* If true, st_?time is float. */
static int _stat_float_times = 1;

PyDoc_STRVAR_remove(stat_float_times__doc__,
"stat_float_times([newval]) -> oldval\n\n\
Determine whether os.[lf]stat represents time stamps as float objects.\n\
If newval is True, future calls to stat() return floats, if it is False,\n\
future calls return ints. \n\
If newval is omitted, return the current setting.\n");

static PyObject*
stat_float_times(PyObject* self, PyObject *args)
{
    int newval = -1;
    if (!PyArg_ParseTuple(args, "|i:stat_float_times", &newval))
        return NULL;
    if (newval == -1)
        /* Return old value */
        return PyBool_FromLong(_stat_float_times);
    _stat_float_times = newval;
    Py_INCREF(Py_None);
    return Py_None;
}

static void
fill_time(PyObject *v, int index, time_t sec, unsigned long nsec)
{
    PyObject *fval,*ival;
#if SIZEOF_TIME_T > SIZEOF_LONG
    ival = PyLong_FromLongLong((PY_LONG_LONG)sec);
#else
    ival = PyInt_FromLong((long)sec);
#endif
    if (!ival)
        return;
    if (_stat_float_times) {
        fval = PyFloat_FromDouble(sec + 1e-9*nsec);
    } else {
        fval = ival;
        Py_INCREF(fval);
    }
    PyStructSequence_SET_ITEM(v, index, ival);
    PyStructSequence_SET_ITEM(v, index+3, fval);
}

/* pack a system stat C structure into the Python stat tuple
   (used by posix_stat() and posix_fstat()) */
static PyObject*
_pystat_fromstructstat(STRUCT_STAT *st)
{
    unsigned long ansec, mnsec, cnsec;
    PyObject *v = PyStructSequence_New(&StatResultType);
    if (v == NULL)
        return NULL;

    PyStructSequence_SET_ITEM(v, 0, PyInt_FromLong((long)st->st_mode));
#ifdef HAVE_LARGEFILE_SUPPORT
    PyStructSequence_SET_ITEM(v, 1,
                              PyLong_FromLongLong((PY_LONG_LONG)st->st_ino));
#else
    PyStructSequence_SET_ITEM(v, 1, PyInt_FromLong((long)st->st_ino));
#endif
#ifdef MS_WINDOWS
    PyStructSequence_SET_ITEM(v, 2, PyLong_FromUnsignedLong(st->st_dev));
#else
    PyStructSequence_SET_ITEM(v, 2, _PyInt_FromDev(st->st_dev));
#endif
    PyStructSequence_SET_ITEM(v, 3, PyInt_FromLong((long)st->st_nlink));
#if defined(MS_WINDOWS)
    PyStructSequence_SET_ITEM(v, 4, PyInt_FromLong(0));
    PyStructSequence_SET_ITEM(v, 5, PyInt_FromLong(0));
#else
    PyStructSequence_SET_ITEM(v, 4, _PyInt_FromUid(st->st_uid));
    PyStructSequence_SET_ITEM(v, 5, _PyInt_FromGid(st->st_gid));
#endif
#ifdef HAVE_LARGEFILE_SUPPORT
    PyStructSequence_SET_ITEM(v, 6,
                              PyLong_FromLongLong((PY_LONG_LONG)st->st_size));
#else
    PyStructSequence_SET_ITEM(v, 6, PyInt_FromLong(st->st_size));
#endif

#if defined(HAVE_STAT_TV_NSEC)
    ansec = st->st_atim.tv_nsec;
    mnsec = st->st_mtim.tv_nsec;
    cnsec = st->st_ctim.tv_nsec;
#elif defined(HAVE_STAT_TV_NSEC2)
    ansec = st->st_atimespec.tv_nsec;
    mnsec = st->st_mtimespec.tv_nsec;
    cnsec = st->st_ctimespec.tv_nsec;
#elif defined(HAVE_STAT_NSEC)
    ansec = st->st_atime_nsec;
    mnsec = st->st_mtime_nsec;
    cnsec = st->st_ctime_nsec;
#else
    ansec = mnsec = cnsec = 0;
#endif
    fill_time(v, 7, st->st_atime, ansec);
    fill_time(v, 8, st->st_mtime, mnsec);
    fill_time(v, 9, st->st_ctime, cnsec);

#ifdef HAVE_STRUCT_STAT_ST_BLKSIZE
    PyStructSequence_SET_ITEM(v, ST_BLKSIZE_IDX,
                              PyInt_FromLong((long)st->st_blksize));
#endif
#ifdef HAVE_STRUCT_STAT_ST_BLOCKS
    PyStructSequence_SET_ITEM(v, ST_BLOCKS_IDX,
                              PyInt_FromLong((long)st->st_blocks));
#endif
#ifdef HAVE_STRUCT_STAT_ST_RDEV
    PyStructSequence_SET_ITEM(v, ST_RDEV_IDX,
                              PyInt_FromLong((long)st->st_rdev));
#endif
#ifdef HAVE_STRUCT_STAT_ST_GEN
    PyStructSequence_SET_ITEM(v, ST_GEN_IDX,
                              PyInt_FromLong((long)st->st_gen));
#endif
#ifdef HAVE_STRUCT_STAT_ST_BIRTHTIME
    {
      PyObject *val;
      unsigned long bsec,bnsec;
      bsec = (long)st->st_birthtime;
#ifdef HAVE_STAT_TV_NSEC2
      bnsec = st->st_birthtimespec.tv_nsec;
#else
      bnsec = 0;
#endif
      if (_stat_float_times) {
        val = PyFloat_FromDouble(bsec + 1e-9*bnsec);
      } else {
        val = PyInt_FromLong((long)bsec);
      }
      PyStructSequence_SET_ITEM(v, ST_BIRTHTIME_IDX,
                                val);
    }
#endif
#ifdef HAVE_STRUCT_STAT_ST_FLAGS
    PyStructSequence_SET_ITEM(v, ST_FLAGS_IDX,
                              PyInt_FromLong((long)st->st_flags));
#endif

    if (PyErr_Occurred()) {
        Py_DECREF(v);
        return NULL;
    }

    return v;
}

static PyObject *
posix_do_stat(PyObject *self, PyObject *args,
              char *format,
              int (*statfunc)(const char *, STRUCT_STAT *),
              char *wformat,
              int (*wstatfunc)(const Py_UNICODE *, STRUCT_STAT *))
{
    STRUCT_STAT st;
    char *path = NULL;          /* pass this to stat; do not free() it */
    char *pathfree = NULL;  /* this memory must be free'd */
    int res;
    PyObject *result;

    if (!PyArg_ParseTuple(args, format,
                          Py_FileSystemDefaultEncoding, &path))
        return NULL;
    pathfree = path;

    Py_BEGIN_ALLOW_THREADS
    res = (*statfunc)(path, &st);
    Py_END_ALLOW_THREADS

    if (res != 0) {
        result = posix_error_with_filename(pathfree);
    }
    else
        result = _pystat_fromstructstat(&st);

    PyMem_Free(pathfree);
    return result;
}

/* POSIX methods */

PyDoc_STRVAR_remove(posix_access__doc__,
"access(path, mode) -> True if granted, False otherwise\n\n\
Use the real uid/gid to test for access to a path.  Note that most\n\
operations will use the effective uid/gid, therefore this routine can\n\
be used in a suid/sgid environment to test if the invoking user has the\n\
specified access to the path.  The mode argument can be F_OK to test\n\
existence, or the inclusive-OR of R_OK, W_OK, and X_OK.");

static PyObject *
posix_access(PyObject *self, PyObject *args)
{
    char *path;
    int mode;

    int res;
    if (!PyArg_ParseTuple(args, "eti:access",
                          Py_FileSystemDefaultEncoding, &path, &mode))
        return NULL;
    Py_BEGIN_ALLOW_THREADS
    res = access(path, mode);
    Py_END_ALLOW_THREADS
    PyMem_Free(path);
    return PyBool_FromLong(res == 0);
}

PyDoc_STRVAR_remove(posix_chdir__doc__,
"chdir(path)\n\n\
Change the current working directory to the specified path.");

static PyObject *
posix_chdir(PyObject *self, PyObject *args)
{
    return posix_1str(args, "et:chdir", chdir);
}

/* OVM_MAIN: Do we need this Solaris workaround??? */

#ifdef HAVE_GETCWD
PyDoc_STRVAR_remove(posix_getcwd__doc__,
"getcwd() -> path\n\n\
Return a string representing the current working directory.");

#if (defined(__sun) && defined(__SVR4)) || \
     defined(__OpenBSD__)               || \
     defined(__NetBSD__)
/* Issue 9185: getcwd() returns NULL/ERANGE indefinitely. */
static PyObject *
posix_getcwd(PyObject *self, PyObject *noargs)
{
    char buf[PATH_MAX+2];
    char *res;

    Py_BEGIN_ALLOW_THREADS
    res = getcwd(buf, sizeof buf);
    Py_END_ALLOW_THREADS

    if (res == NULL)
        return posix_error();

    return PyString_FromString(buf);
}
#else
static PyObject *
posix_getcwd(PyObject *self, PyObject *noargs)
{
    int bufsize_incr = 1024;
    int bufsize = 0;
    char *tmpbuf = NULL;
    char *res = NULL;
    PyObject *dynamic_return;

    Py_BEGIN_ALLOW_THREADS
    do {
        bufsize = bufsize + bufsize_incr;
        tmpbuf = malloc(bufsize);
        if (tmpbuf == NULL) {
            break;
        }
        res = getcwd(tmpbuf, bufsize);

        if (res == NULL) {
            free(tmpbuf);
        }
    } while ((res == NULL) && (errno == ERANGE));
    Py_END_ALLOW_THREADS

    if (res == NULL)
        return posix_error();

    dynamic_return = PyString_FromString(tmpbuf);
    free(tmpbuf);

    return dynamic_return;
}
#endif /* getcwd() NULL/ERANGE workaround. */
#endif /* HAVE_GETCWD */

PyDoc_STRVAR_remove(posix_listdir__doc__,
"listdir(path) -> list_of_strings\n\n\
Return a list containing the names of the entries in the directory.\n\
\n\
    path: path of directory to list\n\
\n\
The list is in arbitrary order.  It does not include the special\n\
entries '.' and '..' even if they are present in the directory.");

static PyObject *
posix_listdir(PyObject *self, PyObject *args)
{
    char *name = NULL;
    PyObject *d, *v;
    DIR *dirp;
    struct dirent *ep;
    int arg_is_unicode = 1;

    errno = 0;
    if (!PyArg_ParseTuple(args, "U:listdir", &v)) {
        arg_is_unicode = 0;
        PyErr_Clear();
    }
    if (!PyArg_ParseTuple(args, "et:listdir", Py_FileSystemDefaultEncoding, &name))
        return NULL;
    Py_BEGIN_ALLOW_THREADS
    dirp = opendir(name);
    Py_END_ALLOW_THREADS
    if (dirp == NULL) {
        return posix_error_with_allocated_filename(name);
    }
    if ((d = PyList_New(0)) == NULL) {
        Py_BEGIN_ALLOW_THREADS
        closedir(dirp);
        Py_END_ALLOW_THREADS
        PyMem_Free(name);
        return NULL;
    }
    for (;;) {
        errno = 0;
        Py_BEGIN_ALLOW_THREADS
        ep = readdir(dirp);
        Py_END_ALLOW_THREADS
        if (ep == NULL) {
            if (errno == 0) {
                break;
            } else {
                Py_BEGIN_ALLOW_THREADS
                closedir(dirp);
                Py_END_ALLOW_THREADS
                Py_DECREF(d);
                return posix_error_with_allocated_filename(name);
            }
        }
        if (ep->d_name[0] == '.' &&
            (NAMLEN(ep) == 1 ||
             (ep->d_name[1] == '.' && NAMLEN(ep) == 2)))
            continue;
        v = PyString_FromStringAndSize(ep->d_name, NAMLEN(ep));
        if (v == NULL) {
            Py_DECREF(d);
            d = NULL;
            break;
        }
#ifdef Py_USING_UNICODE
        if (arg_is_unicode) {
            PyObject *w;

            w = PyUnicode_FromEncodedObject(v,
                                            Py_FileSystemDefaultEncoding,
                                            "strict");
            if (w != NULL) {
                Py_DECREF(v);
                v = w;
            }
            else {
                /* fall back to the original byte string, as
                   discussed in patch #683592 */
                PyErr_Clear();
            }
        }
#endif
        if (PyList_Append(d, v) != 0) {
            Py_DECREF(v);
            Py_DECREF(d);
            d = NULL;
            break;
        }
        Py_DECREF(v);
    }
    Py_BEGIN_ALLOW_THREADS
    closedir(dirp);
    Py_END_ALLOW_THREADS
    PyMem_Free(name);

    return d;
}  /* end of posix_listdir */

PyDoc_STRVAR_remove(posix_mkdir__doc__,
"mkdir(path [, mode=0777])\n\n\
Create a directory.");

static PyObject *
posix_mkdir(PyObject *self, PyObject *args)
{
    int res;
    char *path = NULL;
    int mode = 0777;

    if (!PyArg_ParseTuple(args, "et|i:mkdir",
                          Py_FileSystemDefaultEncoding, &path, &mode))
        return NULL;
    Py_BEGIN_ALLOW_THREADS
    res = mkdir(path, mode);
    Py_END_ALLOW_THREADS
    if (res < 0)
        return posix_error_with_allocated_filename(path);
    PyMem_Free(path);
    Py_INCREF(Py_None);
    return Py_None;
}


PyDoc_STRVAR_remove(posix_rename__doc__,
"rename(old, new)\n\n\
Rename a file or directory.");

static PyObject *
posix_rename(PyObject *self, PyObject *args)
{
    return posix_2str(args, "etet:rename", rename);
}


PyDoc_STRVAR_remove(posix_rmdir__doc__,
"rmdir(path)\n\n\
Remove a directory.");

static PyObject *
posix_rmdir(PyObject *self, PyObject *args)
{
    return posix_1str(args, "et:rmdir", rmdir);
}


PyDoc_STRVAR_remove(posix_stat__doc__,
"stat(path) -> stat result\n\n\
Perform a stat system call on the given path.");

static PyObject *
posix_stat(PyObject *self, PyObject *args)
{
    return posix_do_stat(self, args, "et:stat", STAT, NULL, NULL);
}

PyDoc_STRVAR_remove(posix_umask__doc__,
"umask(new_mask) -> old_mask\n\n\
Set the current numeric umask and return the previous umask.");

static PyObject *
posix_umask(PyObject *self, PyObject *args)
{
    int i;
    if (!PyArg_ParseTuple(args, "i:umask", &i))
        return NULL;
    i = (int)umask(i);
    if (i < 0)
        return posix_error();
    return PyInt_FromLong((long)i);
}


PyDoc_STRVAR_remove(posix_unlink__doc__,
"unlink(path)\n\n\
Remove a file (same as remove(path)).");

PyDoc_STRVAR_remove(posix_remove__doc__,
"remove(path)\n\n\
Remove a file (same as unlink(path)).");

static PyObject *
posix_unlink(PyObject *self, PyObject *args)
{
    return posix_1str(args, "et:remove", unlink);
}


#ifdef HAVE_UNAME
PyDoc_STRVAR_remove(posix_uname__doc__,
"uname() -> (sysname, nodename, release, version, machine)\n\n\
Return a tuple identifying the current operating system.");

static PyObject *
posix_uname(PyObject *self, PyObject *noargs)
{
    struct utsname u;
    int res;

    Py_BEGIN_ALLOW_THREADS
    res = uname(&u);
    Py_END_ALLOW_THREADS
    if (res < 0)
        return posix_error();
    return Py_BuildValue("(sssss)",
                         u.sysname,
                         u.nodename,
                         u.release,
                         u.version,
                         u.machine);
}
#endif /* HAVE_UNAME */

/* Process operations */

PyDoc_STRVAR_remove(posix__exit__doc__,
"_exit(status)\n\n\
Exit to the system with specified status, without normal exit processing.");

static PyObject *
posix__exit(PyObject *self, PyObject *args)
{
    int sts;
    if (!PyArg_ParseTuple(args, "i:_exit", &sts))
        return NULL;
    _exit(sts);
    return NULL; /* Make gcc -Wall happy */
}

#if defined(HAVE_EXECV) || defined(HAVE_SPAWNV)
static void
free_string_array(char **array, Py_ssize_t count)
{
    Py_ssize_t i;
    for (i = 0; i < count; i++)
        PyMem_Free(array[i]);
    PyMem_DEL(array);
}
#endif


#ifdef HAVE_EXECV
PyDoc_STRVAR_remove(posix_execv__doc__,
"execv(path, args)\n\n\
Execute an executable path with arguments, replacing current process.\n\
\n\
    path: path of executable file\n\
    args: tuple or list of strings");

static PyObject *
posix_execv(PyObject *self, PyObject *args)
{
    char *path;
    PyObject *argv;
    char **argvlist;
    Py_ssize_t i, argc;
    PyObject *(*getitem)(PyObject *, Py_ssize_t);

    /* execv has two arguments: (path, argv), where
       argv is a list or tuple of strings. */

    if (!PyArg_ParseTuple(args, "etO:execv",
                          Py_FileSystemDefaultEncoding,
                          &path, &argv))
        return NULL;
    if (PyList_Check(argv)) {
        argc = PyList_Size(argv);
        getitem = PyList_GetItem;
    }
    else if (PyTuple_Check(argv)) {
        argc = PyTuple_Size(argv);
        getitem = PyTuple_GetItem;
    }
    else {
        PyErr_SetString(PyExc_TypeError, "execv() arg 2 must be a tuple or list");
        PyMem_Free(path);
        return NULL;
    }
    if (argc < 1) {
        PyErr_SetString(PyExc_ValueError, "execv() arg 2 must not be empty");
        PyMem_Free(path);
        return NULL;
    }

    argvlist = PyMem_NEW(char *, argc+1);
    if (argvlist == NULL) {
        PyMem_Free(path);
        return PyErr_NoMemory();
    }
    for (i = 0; i < argc; i++) {
        if (!PyArg_Parse((*getitem)(argv, i), "et",
                         Py_FileSystemDefaultEncoding,
                         &argvlist[i])) {
            free_string_array(argvlist, i);
            PyErr_SetString(PyExc_TypeError,
                            "execv() arg 2 must contain only strings");
            PyMem_Free(path);
            return NULL;

        }
    }
    argvlist[argc] = NULL;

    execv(path, argvlist);

    /* If we get here it's definitely an error */

    free_string_array(argvlist, argc);
    PyMem_Free(path);
    return posix_error();
}


PyDoc_STRVAR_remove(posix_execve__doc__,
"execve(path, args, env)\n\n\
Execute a path with arguments and environment, replacing current process.\n\
\n\
    path: path of executable file\n\
    args: tuple or list of arguments\n\
    env: dictionary of strings mapping to strings");

static PyObject *
posix_execve(PyObject *self, PyObject *args)
{
    char *path;
    PyObject *argv, *env;
    char **argvlist;
    char **envlist;
    PyObject *key, *val, *keys=NULL, *vals=NULL;
    Py_ssize_t i, pos, argc, envc;
    PyObject *(*getitem)(PyObject *, Py_ssize_t);
    Py_ssize_t lastarg = 0;

    /* execve has three arguments: (path, argv, env), where
       argv is a list or tuple of strings and env is a dictionary
       like posix.environ. */

    if (!PyArg_ParseTuple(args, "etOO:execve",
                          Py_FileSystemDefaultEncoding,
                          &path, &argv, &env))
        return NULL;
    if (PyList_Check(argv)) {
        argc = PyList_Size(argv);
        getitem = PyList_GetItem;
    }
    else if (PyTuple_Check(argv)) {
        argc = PyTuple_Size(argv);
        getitem = PyTuple_GetItem;
    }
    else {
        PyErr_SetString(PyExc_TypeError,
                        "execve() arg 2 must be a tuple or list");
        goto fail_0;
    }
    if (!PyMapping_Check(env)) {
        PyErr_SetString(PyExc_TypeError,
                        "execve() arg 3 must be a mapping object");
        goto fail_0;
    }

    argvlist = PyMem_NEW(char *, argc+1);
    if (argvlist == NULL) {
        PyErr_NoMemory();
        goto fail_0;
    }
    for (i = 0; i < argc; i++) {
        if (!PyArg_Parse((*getitem)(argv, i),
                         "et;execve() arg 2 must contain only strings",
                         Py_FileSystemDefaultEncoding,
                         &argvlist[i]))
        {
            lastarg = i;
            goto fail_1;
        }
    }
    lastarg = argc;
    argvlist[argc] = NULL;

    i = PyMapping_Size(env);
    if (i < 0)
        goto fail_1;
    envlist = PyMem_NEW(char *, i + 1);
    if (envlist == NULL) {
        PyErr_NoMemory();
        goto fail_1;
    }
    envc = 0;
    keys = PyMapping_Keys(env);
    vals = PyMapping_Values(env);
    if (!keys || !vals)
        goto fail_2;
    if (!PyList_Check(keys) || !PyList_Check(vals)) {
        PyErr_SetString(PyExc_TypeError,
                        "execve(): env.keys() or env.values() is not a list");
        goto fail_2;
    }

    for (pos = 0; pos < i; pos++) {
        char *p, *k, *v;
        size_t len;

        key = PyList_GetItem(keys, pos);
        val = PyList_GetItem(vals, pos);
        if (!key || !val)
            goto fail_2;

        if (!PyArg_Parse(
                    key,
                    "s;execve() arg 3 contains a non-string key",
                    &k) ||
            !PyArg_Parse(
                val,
                "s;execve() arg 3 contains a non-string value",
                &v))
        {
            goto fail_2;
        }

        len = PyString_Size(key) + PyString_Size(val) + 2;
        p = PyMem_NEW(char, len);
        if (p == NULL) {
            PyErr_NoMemory();
            goto fail_2;
        }
        PyOS_snprintf(p, len, "%s=%s", k, v);
        envlist[envc++] = p;
    }
    envlist[envc] = 0;

    execve(path, argvlist, envlist);

    /* If we get here it's definitely an error */

    (void) posix_error();

  fail_2:
    while (--envc >= 0)
        PyMem_DEL(envlist[envc]);
    PyMem_DEL(envlist);
  fail_1:
    free_string_array(argvlist, lastarg);
    Py_XDECREF(vals);
    Py_XDECREF(keys);
  fail_0:
    PyMem_Free(path);
    return NULL;
}
#endif /* HAVE_EXECV */

#ifdef HAVE_FORK
PyDoc_STRVAR_remove(posix_fork__doc__,
"fork() -> pid\n\n\
Fork a child process.\n\
Return 0 to child process and PID of child to parent process.");

static PyObject *
posix_fork(PyObject *self, PyObject *noargs)
{
    pid_t pid;
    int result = 0;
    _PyImport_AcquireLock();
    pid = fork();
    if (pid == 0) {
        /* child: this clobbers and resets the import lock. */
        PyOS_AfterFork();
    } else {
        /* parent: release the import lock. */
        result = _PyImport_ReleaseLock();
    }
    if (pid == -1)
        return posix_error();
    if (result < 0) {
        /* Don't clobber the OSError if the fork failed. */
        PyErr_SetString(PyExc_RuntimeError,
                        "not holding the import lock");
        return NULL;
    }
    return PyLong_FromPid(pid);
}
#endif

#ifdef HAVE_GETEGID
PyDoc_STRVAR_remove(posix_getegid__doc__,
"getegid() -> egid\n\n\
Return the current process's effective group id.");

static PyObject *
posix_getegid(PyObject *self, PyObject *noargs)
{
    return _PyInt_FromGid(getegid());
}
#endif


#ifdef HAVE_GETEUID
PyDoc_STRVAR_remove(posix_geteuid__doc__,
"geteuid() -> euid\n\n\
Return the current process's effective user id.");

static PyObject *
posix_geteuid(PyObject *self, PyObject *noargs)
{
    return _PyInt_FromUid(geteuid());
}
#endif


#ifdef HAVE_GETGID
PyDoc_STRVAR_remove(posix_getgid__doc__,
"getgid() -> gid\n\n\
Return the current process's group id.");

static PyObject *
posix_getgid(PyObject *self, PyObject *noargs)
{
    return _PyInt_FromGid(getgid());
}
#endif


PyDoc_STRVAR_remove(posix_getpid__doc__,
"getpid() -> pid\n\n\
Return the current process id");

static PyObject *
posix_getpid(PyObject *self, PyObject *noargs)
{
    return PyLong_FromPid(getpid());
}

#ifdef HAVE_GETPGID
PyDoc_STRVAR_remove(posix_getpgid__doc__,
"getpgid(pid) -> pgid\n\n\
Call the system call getpgid().");

static PyObject *
posix_getpgid(PyObject *self, PyObject *args)
{
    pid_t pid, pgid;
    if (!PyArg_ParseTuple(args, PARSE_PID ":getpgid", &pid))
        return NULL;
    pgid = getpgid(pid);
    if (pgid < 0)
        return posix_error();
    return PyLong_FromPid(pgid);
}
#endif /* HAVE_GETPGID */


#ifdef HAVE_GETPPID
PyDoc_STRVAR_remove(posix_getppid__doc__,
"getppid() -> ppid\n\n\
Return the parent's process id.");

static PyObject *
posix_getppid(PyObject *self, PyObject *noargs)
{
    return PyLong_FromPid(getppid());
}
#endif


#ifdef HAVE_GETUID
PyDoc_STRVAR_remove(posix_getuid__doc__,
"getuid() -> uid\n\n\
Return the current process's user id.");

static PyObject *
posix_getuid(PyObject *self, PyObject *noargs)
{
    return _PyInt_FromUid(getuid());
}
#endif


#ifdef HAVE_KILL
PyDoc_STRVAR_remove(posix_kill__doc__,
"kill(pid, sig)\n\n\
Kill a process with a signal.");

static PyObject *
posix_kill(PyObject *self, PyObject *args)
{
    pid_t pid;
    int sig;
    if (!PyArg_ParseTuple(args, PARSE_PID "i:kill", &pid, &sig))
        return NULL;
    if (kill(pid, sig) == -1)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}
#endif

#ifdef HAVE_KILLPG
PyDoc_STRVAR_remove(posix_killpg__doc__,
"killpg(pgid, sig)\n\n\
Kill a process group with a signal.");

static PyObject *
posix_killpg(PyObject *self, PyObject *args)
{
    int sig;
    pid_t pgid;
    /* XXX some man pages make the `pgid` parameter an int, others
       a pid_t. Since getpgrp() returns a pid_t, we assume killpg should
       take the same type. Moreover, pid_t is always at least as wide as
       int (else compilation of this module fails), which is safe. */
    if (!PyArg_ParseTuple(args, PARSE_PID "i:killpg", &pgid, &sig))
        return NULL;
    if (killpg(pgid, sig) == -1)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}
#endif

#ifdef HAVE_SETUID
PyDoc_STRVAR_remove(posix_setuid__doc__,
"setuid(uid)\n\n\
Set the current process's user id.");

static PyObject *
posix_setuid(PyObject *self, PyObject *args)
{
    uid_t uid;
    if (!PyArg_ParseTuple(args, "O&:setuid", _Py_Uid_Converter, &uid))
        return NULL;
    if (setuid(uid) < 0)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}
#endif /* HAVE_SETUID */


#ifdef HAVE_SETEUID
PyDoc_STRVAR_remove(posix_seteuid__doc__,
"seteuid(uid)\n\n\
Set the current process's effective user id.");

static PyObject *
posix_seteuid (PyObject *self, PyObject *args)
{
    uid_t euid;
    if (!PyArg_ParseTuple(args, "O&:seteuid", _Py_Uid_Converter, &euid))
        return NULL;
    if (seteuid(euid) < 0) {
        return posix_error();
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}
#endif /* HAVE_SETEUID */

#ifdef HAVE_SETEGID
PyDoc_STRVAR_remove(posix_setegid__doc__,
"setegid(gid)\n\n\
Set the current process's effective group id.");

static PyObject *
posix_setegid (PyObject *self, PyObject *args)
{
    gid_t egid;
    if (!PyArg_ParseTuple(args, "O&:setegid", _Py_Gid_Converter, &egid))
        return NULL;
    if (setegid(egid) < 0) {
        return posix_error();
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}
#endif /* HAVE_SETEGID */

#ifdef HAVE_SETREUID
PyDoc_STRVAR_remove(posix_setreuid__doc__,
"setreuid(ruid, euid)\n\n\
Set the current process's real and effective user ids.");

static PyObject *
posix_setreuid (PyObject *self, PyObject *args)
{
    uid_t ruid, euid;
    if (!PyArg_ParseTuple(args, "O&O&:setreuid",
                          _Py_Uid_Converter, &ruid,
                          _Py_Uid_Converter, &euid))
        return NULL;
    if (setreuid(ruid, euid) < 0) {
        return posix_error();
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}
#endif /* HAVE_SETREUID */

#ifdef HAVE_SETREGID
PyDoc_STRVAR_remove(posix_setregid__doc__,
"setregid(rgid, egid)\n\n\
Set the current process's real and effective group ids.");

static PyObject *
posix_setregid (PyObject *self, PyObject *args)
{
    gid_t rgid, egid;
    if (!PyArg_ParseTuple(args, "O&O&:setregid",
                          _Py_Gid_Converter, &rgid,
                          _Py_Gid_Converter, &egid))
        return NULL;
    if (setregid(rgid, egid) < 0) {
        return posix_error();
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}
#endif /* HAVE_SETREGID */

#ifdef HAVE_SETGID
PyDoc_STRVAR_remove(posix_setgid__doc__,
"setgid(gid)\n\n\
Set the current process's group id.");

static PyObject *
posix_setgid(PyObject *self, PyObject *args)
{
    gid_t gid;
    if (!PyArg_ParseTuple(args, "O&:setgid", _Py_Gid_Converter, &gid))
        return NULL;
    if (setgid(gid) < 0)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}
#endif /* HAVE_SETGID */

#if defined(HAVE_WAIT3) || defined(HAVE_WAIT4)
static PyObject *
wait_helper(pid_t pid, int status, struct rusage *ru)
{
    PyObject *result;
    static PyObject *struct_rusage;

    if (pid == -1)
        return posix_error();

    if (struct_rusage == NULL) {
        PyObject *m = PyImport_ImportModuleNoBlock("resource");
        if (m == NULL)
            return NULL;
        struct_rusage = PyObject_GetAttrString(m, "struct_rusage");
        Py_DECREF(m);
        if (struct_rusage == NULL)
            return NULL;
    }

    /* XXX(nnorwitz): Copied (w/mods) from resource.c, there should be only one. */
    result = PyStructSequence_New((PyTypeObject*) struct_rusage);
    if (!result)
        return NULL;

#ifndef doubletime
#define doubletime(TV) ((double)(TV).tv_sec + (TV).tv_usec * 0.000001)
#endif

    PyStructSequence_SET_ITEM(result, 0,
                              PyFloat_FromDouble(doubletime(ru->ru_utime)));
    PyStructSequence_SET_ITEM(result, 1,
                              PyFloat_FromDouble(doubletime(ru->ru_stime)));
#define SET_INT(result, index, value)\
        PyStructSequence_SET_ITEM(result, index, PyInt_FromLong(value))
    SET_INT(result, 2, ru->ru_maxrss);
    SET_INT(result, 3, ru->ru_ixrss);
    SET_INT(result, 4, ru->ru_idrss);
    SET_INT(result, 5, ru->ru_isrss);
    SET_INT(result, 6, ru->ru_minflt);
    SET_INT(result, 7, ru->ru_majflt);
    SET_INT(result, 8, ru->ru_nswap);
    SET_INT(result, 9, ru->ru_inblock);
    SET_INT(result, 10, ru->ru_oublock);
    SET_INT(result, 11, ru->ru_msgsnd);
    SET_INT(result, 12, ru->ru_msgrcv);
    SET_INT(result, 13, ru->ru_nsignals);
    SET_INT(result, 14, ru->ru_nvcsw);
    SET_INT(result, 15, ru->ru_nivcsw);
#undef SET_INT

    if (PyErr_Occurred()) {
        Py_DECREF(result);
        return NULL;
    }

    return Py_BuildValue("NiN", PyLong_FromPid(pid), status, result);
}
#endif /* HAVE_WAIT3 || HAVE_WAIT4 */

#ifdef HAVE_WAIT3
PyDoc_STRVAR_remove(posix_wait3__doc__,
"wait3(options) -> (pid, status, rusage)\n\n\
Wait for completion of a child process.");

static PyObject *
posix_wait3(PyObject *self, PyObject *args)
{
    pid_t pid;
    int options;
    struct rusage ru;
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:wait3", &options))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    pid = wait3(&status, options, &ru);
    Py_END_ALLOW_THREADS

    return wait_helper(pid, WAIT_STATUS_INT(status), &ru);
}
#endif /* HAVE_WAIT3 */

#ifdef HAVE_WAIT4
PyDoc_STRVAR_remove(posix_wait4__doc__,
"wait4(pid, options) -> (pid, status, rusage)\n\n\
Wait for completion of a given child process.");

static PyObject *
posix_wait4(PyObject *self, PyObject *args)
{
    pid_t pid;
    int options;
    struct rusage ru;
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, PARSE_PID "i:wait4", &pid, &options))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    pid = wait4(pid, &status, options, &ru);
    Py_END_ALLOW_THREADS

    return wait_helper(pid, WAIT_STATUS_INT(status), &ru);
}
#endif /* HAVE_WAIT4 */

#ifdef HAVE_WAITPID
PyDoc_STRVAR_remove(posix_waitpid__doc__,
"waitpid(pid, options) -> (pid, status)\n\n\
Wait for completion of a given child process.");

static PyObject *
posix_waitpid(PyObject *self, PyObject *args)
{
    pid_t pid;
    int options;
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, PARSE_PID "i:waitpid", &pid, &options))
        return NULL;
    while (1) {
        Py_BEGIN_ALLOW_THREADS
        pid = waitpid(pid, &status, options);
        Py_END_ALLOW_THREADS

        if (pid >= 0) {  // success
            break;
        } else {
            if (PyErr_CheckSignals()) {
                return NULL;  // Propagate KeyboardInterrupt
            }
            if (errno != EINTR) {  // e.g. ECHILD
                return posix_error();
            }
        }
        // Otherwise, try again on EINTR.
    }

    return Py_BuildValue("Ni", PyLong_FromPid(pid), WAIT_STATUS_INT(status));
}
#endif /* HAVE_WAITPID */

#ifdef HAVE_WAIT
PyDoc_STRVAR_remove(posix_wait__doc__,
"wait() -> (pid, status)\n\n\
Wait for completion of a child process.");

static PyObject *
posix_wait(PyObject *self, PyObject *noargs)
{
    pid_t pid;
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    // OVM_MAIN patch: Retry on EINTR.
    while (1) {
        Py_BEGIN_ALLOW_THREADS
        pid = wait(&status);
        Py_END_ALLOW_THREADS

        if (pid >= 0) {  // success
            break;
        } else {
            if (PyErr_CheckSignals()) {
                return NULL;  // Propagate KeyboardInterrupt
            }
            if (errno != EINTR) {  // e.g. ECHILD
                return posix_error();
            }
        }
        // Otherwise, try again on EINTR.
    }

    return Py_BuildValue("Ni", PyLong_FromPid(pid), WAIT_STATUS_INT(status));
}
#endif


PyDoc_STRVAR_remove(posix_lstat__doc__,
"lstat(path) -> stat result\n\n\
Like stat(path), but do not follow symbolic links.");

static PyObject *
posix_lstat(PyObject *self, PyObject *args)
{
#ifdef HAVE_LSTAT
    return posix_do_stat(self, args, "et:lstat", lstat, NULL, NULL);
#else /* !HAVE_LSTAT */
    return posix_do_stat(self, args, "et:lstat", STAT, NULL, NULL);
#endif /* !HAVE_LSTAT */
}


#ifdef HAVE_READLINK
PyDoc_STRVAR_remove(posix_readlink__doc__,
"readlink(path) -> path\n\n\
Return a string representing the path to which the symbolic link points.");

static PyObject *
posix_readlink(PyObject *self, PyObject *args)
{
    PyObject* v;
    char buf[MAXPATHLEN];
    char *path;
    int n;
#ifdef Py_USING_UNICODE
    int arg_is_unicode = 0;
#endif

    if (!PyArg_ParseTuple(args, "et:readlink",
                          Py_FileSystemDefaultEncoding, &path))
        return NULL;
#ifdef Py_USING_UNICODE
    v = PySequence_GetItem(args, 0);
    if (v == NULL) {
        PyMem_Free(path);
        return NULL;
    }

    if (PyUnicode_Check(v)) {
        arg_is_unicode = 1;
    }
    Py_DECREF(v);
#endif

    Py_BEGIN_ALLOW_THREADS
    n = readlink(path, buf, (int) sizeof buf);
    Py_END_ALLOW_THREADS
    if (n < 0)
        return posix_error_with_allocated_filename(path);

    PyMem_Free(path);
    v = PyString_FromStringAndSize(buf, n);
#ifdef Py_USING_UNICODE
    if (arg_is_unicode) {
        PyObject *w;

        w = PyUnicode_FromEncodedObject(v,
                                        Py_FileSystemDefaultEncoding,
                                        "strict");
        if (w != NULL) {
            Py_DECREF(v);
            v = w;
        }
        else {
            /* fall back to the original byte string, as
               discussed in patch #683592 */
            PyErr_Clear();
        }
    }
#endif
    return v;
}
#endif /* HAVE_READLINK */


#ifdef HAVE_SYMLINK
PyDoc_STRVAR_remove(posix_symlink__doc__,
"symlink(src, dst)\n\n\
Create a symbolic link pointing to src named dst.");

static PyObject *
posix_symlink(PyObject *self, PyObject *args)
{
    return posix_2str(args, "etet:symlink", symlink);
}
#endif /* HAVE_SYMLINK */


#ifdef HAVE_TIMES
#define NEED_TICKS_PER_SECOND
static long ticks_per_second = -1;
static PyObject *
posix_times(PyObject *self, PyObject *noargs)
{
    struct tms t;
    clock_t c;
    errno = 0;
    c = times(&t);
    if (c == (clock_t) -1)
        return posix_error();
    return Py_BuildValue("ddddd",
                         (double)t.tms_utime / ticks_per_second,
                         (double)t.tms_stime / ticks_per_second,
                         (double)t.tms_cutime / ticks_per_second,
                         (double)t.tms_cstime / ticks_per_second,
                         (double)c / ticks_per_second);
}
#endif /* HAVE_TIMES */


#ifdef HAVE_TIMES
PyDoc_STRVAR_remove(posix_times__doc__,
"times() -> (utime, stime, cutime, cstime, elapsed_time)\n\n\
Return a tuple of floating point numbers indicating process times.");
#endif


#ifdef HAVE_GETSID
PyDoc_STRVAR_remove(posix_getsid__doc__,
"getsid(pid) -> sid\n\n\
Call the system call getsid().");

static PyObject *
posix_getsid(PyObject *self, PyObject *args)
{
    pid_t pid;
    int sid;
    if (!PyArg_ParseTuple(args, PARSE_PID ":getsid", &pid))
        return NULL;
    sid = getsid(pid);
    if (sid < 0)
        return posix_error();
    return PyInt_FromLong((long)sid);
}
#endif /* HAVE_GETSID */


#ifdef HAVE_SETSID
PyDoc_STRVAR_remove(posix_setsid__doc__,
"setsid()\n\n\
Call the system call setsid().");

static PyObject *
posix_setsid(PyObject *self, PyObject *noargs)
{
    if (setsid() < 0)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}
#endif /* HAVE_SETSID */

#ifdef HAVE_SETPGID
PyDoc_STRVAR_remove(posix_setpgid__doc__,
"setpgid(pid, pgrp)\n\n\
Call the system call setpgid().");

static PyObject *
posix_setpgid(PyObject *self, PyObject *args)
{
    pid_t pid;
    int pgrp;
    if (!PyArg_ParseTuple(args, PARSE_PID "i:setpgid", &pid, &pgrp))
        return NULL;
    if (setpgid(pid, pgrp) < 0)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}
#endif /* HAVE_SETPGID */


#ifdef HAVE_TCGETPGRP
PyDoc_STRVAR_remove(posix_tcgetpgrp__doc__,
"tcgetpgrp(fd) -> pgid\n\n\
Return the process group associated with the terminal given by a fd.");

static PyObject *
posix_tcgetpgrp(PyObject *self, PyObject *args)
{
    int fd;
    pid_t pgid;
    if (!PyArg_ParseTuple(args, "i:tcgetpgrp", &fd))
        return NULL;
    pgid = tcgetpgrp(fd);
    if (pgid < 0)
        return posix_error();
    return PyLong_FromPid(pgid);
}
#endif /* HAVE_TCGETPGRP */


#ifdef HAVE_TCSETPGRP
PyDoc_STRVAR_remove(posix_tcsetpgrp__doc__,
"tcsetpgrp(fd, pgid)\n\n\
Set the process group associated with the terminal given by a fd.");

static PyObject *
posix_tcsetpgrp(PyObject *self, PyObject *args)
{
    int fd;
    pid_t pgid;
    if (!PyArg_ParseTuple(args, "i" PARSE_PID ":tcsetpgrp", &fd, &pgid))
        return NULL;
    if (tcsetpgrp(fd, pgid) < 0)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}
#endif /* HAVE_TCSETPGRP */

/* Functions acting on file descriptors */

PyDoc_STRVAR_remove(posix_open__doc__,
"open(filename, flag [, mode=0777]) -> fd\n\n\
Open a file (for low level IO).");

static PyObject *
posix_open(PyObject *self, PyObject *args)
{
    char *file = NULL;
    int flag;
    int mode = 0777;
    int fd;

    if (!PyArg_ParseTuple(args, "eti|i",
                          Py_FileSystemDefaultEncoding, &file,
                          &flag, &mode))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    fd = open(file, flag, mode);
    Py_END_ALLOW_THREADS
    if (fd < 0)
        return posix_error_with_allocated_filename(file);
    PyMem_Free(file);
    return PyInt_FromLong((long)fd);
}


PyDoc_STRVAR_remove(posix_close__doc__,
"close(fd)\n\n\
Close a file descriptor (for low level IO).");

/*
The underscore at end of function name avoids a name clash with the libc
function posix_close.
*/
static PyObject *
posix_close_(PyObject *self, PyObject *args)
{
    int fd, res;
    if (!PyArg_ParseTuple(args, "i:close", &fd))
        return NULL;
    if (!_PyVerify_fd(fd))
        return posix_error();
    Py_BEGIN_ALLOW_THREADS
    res = close(fd);
    Py_END_ALLOW_THREADS
    if (res < 0)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR_remove(posix_dup__doc__,
"dup(fd) -> fd2\n\n\
Return a duplicate of a file descriptor.");

static PyObject *
posix_dup(PyObject *self, PyObject *args)
{
    int fd;
    if (!PyArg_ParseTuple(args, "i:dup", &fd))
        return NULL;
    if (!_PyVerify_fd(fd))
        return posix_error();
    Py_BEGIN_ALLOW_THREADS
    fd = dup(fd);
    Py_END_ALLOW_THREADS
    if (fd < 0)
        return posix_error();
    return PyInt_FromLong((long)fd);
}


PyDoc_STRVAR_remove(posix_dup2__doc__,
"dup2(old_fd, new_fd)\n\n\
Duplicate file descriptor.");

static PyObject *
posix_dup2(PyObject *self, PyObject *args)
{
    int fd, fd2, res;
    if (!PyArg_ParseTuple(args, "ii:dup2", &fd, &fd2))
        return NULL;
    Py_BEGIN_ALLOW_THREADS
    res = dup2(fd, fd2);
    Py_END_ALLOW_THREADS
    if (res < 0)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}


PyDoc_STRVAR_remove(posix_read__doc__,
"read(fd, buffersize) -> string\n\n\
Read a file descriptor.");

static PyObject *
posix_read(PyObject *self, PyObject *args)
{
    int fd, size, n;
    PyObject *buffer;
    if (!PyArg_ParseTuple(args, "ii:read", &fd, &size))
        return NULL;
    if (size < 0) {
        errno = EINVAL;
        return posix_error();
    }
    buffer = PyString_FromStringAndSize((char *)NULL, size);
    if (buffer == NULL)
        return NULL;
    if (!_PyVerify_fd(fd)) {
        Py_DECREF(buffer);
        return posix_error();
    }
    // OVM_MAIN patch: Retry on EINTR.
    while (1) {
        Py_BEGIN_ALLOW_THREADS
        n = read(fd, PyString_AsString(buffer), size);
        Py_END_ALLOW_THREADS

        if (n >= 0) {  // success
            break;
        } else {
            if (PyErr_CheckSignals()) {
                return NULL;  // Propagate KeyboardInterrupt
            }
            if (errno != EINTR) {
                Py_DECREF(buffer);
                return posix_error();
            }
        }
        // Otherwise, try again on EINTR.
    }
    if (n != size)
        _PyString_Resize(&buffer, n);
    return buffer;
}


PyDoc_STRVAR_remove(posix_write__doc__,
"write(fd, string) -> byteswritten\n\n\
Write a string to a file descriptor.");

static PyObject *
posix_write(PyObject *self, PyObject *args)
{
    Py_buffer pbuf;
    int fd;
    Py_ssize_t size, len;

    if (!PyArg_ParseTuple(args, "is*:write", &fd, &pbuf))
        return NULL;
    if (!_PyVerify_fd(fd)) {
        PyBuffer_Release(&pbuf);
        return posix_error();
    }
    len = pbuf.len;

    // OVM_MAIN patch: Retry on EINTR.
    while (1) {
        Py_BEGIN_ALLOW_THREADS
        size = write(fd, pbuf.buf, len);
        Py_END_ALLOW_THREADS

        if (size >= 0) {  // success
            break;
        } else {
            if (PyErr_CheckSignals()) {
                return NULL;  // Propagate KeyboardInterrupt
            }
            if (errno != EINTR) {
                return posix_error();
            }
        }
    }
    PyBuffer_Release(&pbuf);
    return PyInt_FromSsize_t(size);
}


PyDoc_STRVAR_remove(posix_fstat__doc__,
"fstat(fd) -> stat result\n\n\
Like stat(), but for an open file descriptor.");

static PyObject *
posix_fstat(PyObject *self, PyObject *args)
{
    int fd;
    STRUCT_STAT st;
    int res;
    if (!PyArg_ParseTuple(args, "i:fstat", &fd))
        return NULL;
#ifdef __VMS
    /* on OpenVMS we must ensure that all bytes are written to the file */
    fsync(fd);
#endif
    if (!_PyVerify_fd(fd))
        return posix_error();
    Py_BEGIN_ALLOW_THREADS
    res = FSTAT(fd, &st);
    Py_END_ALLOW_THREADS
    if (res != 0) {
        return posix_error();
    }

    return _pystat_fromstructstat(&st);
}


PyDoc_STRVAR_remove(posix_fdopen__doc__,
"fdopen(fd [, mode='r' [, bufsize]]) -> file_object\n\n\
Return an open file object connected to a file descriptor.");

static PyObject *
posix_fdopen(PyObject *self, PyObject *args)
{
    int fd;
    char *orgmode = "r";
    int bufsize = -1;
    FILE *fp;
    PyObject *f;
    char *mode;
    if (!PyArg_ParseTuple(args, "i|si", &fd, &orgmode, &bufsize))
        return NULL;

    /* Sanitize mode.  See fileobject.c */
    mode = PyMem_MALLOC(strlen(orgmode)+3);
    if (!mode) {
        PyErr_NoMemory();
        return NULL;
    }
    strcpy(mode, orgmode);
    if (_PyFile_SanitizeMode(mode)) {
        PyMem_FREE(mode);
        return NULL;
    }
    if (!_PyVerify_fd(fd)) {
        PyMem_FREE(mode);
        return posix_error();
    }
#if defined(HAVE_FSTAT) && defined(S_IFDIR) && defined(EISDIR)
    {
        struct stat buf;
        const char *msg;
        PyObject *exc;
        if (fstat(fd, &buf) == 0 && S_ISDIR(buf.st_mode)) {
            PyMem_FREE(mode);
            msg = strerror(EISDIR);
            exc = PyObject_CallFunction(PyExc_IOError, "(iss)",
                                        EISDIR, msg, "<fdopen>");
            if (exc) {
                PyErr_SetObject(PyExc_IOError, exc);
                Py_DECREF(exc);
            }
            return NULL;
        }
    }
#endif
    /* The dummy filename used here must be kept in sync with the value
       tested against in gzip.GzipFile.__init__() - see issue #13781. */
    f = PyFile_FromFile(NULL, "<fdopen>", orgmode, fclose);
    if (f == NULL) {
        PyMem_FREE(mode);
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS
#if !defined(MS_WINDOWS) && defined(HAVE_FCNTL_H)
    if (mode[0] == 'a') {
        /* try to make sure the O_APPEND flag is set */
        int flags;
        flags = fcntl(fd, F_GETFL);
        if (flags != -1)
            fcntl(fd, F_SETFL, flags | O_APPEND);
        fp = fdopen(fd, mode);
        if (fp == NULL && flags != -1)
            /* restore old mode if fdopen failed */
            fcntl(fd, F_SETFL, flags);
    } else {
        fp = fdopen(fd, mode);
    }
#else
    fp = fdopen(fd, mode);
#endif
    Py_END_ALLOW_THREADS
    PyMem_FREE(mode);
    if (fp == NULL) {
        Py_DECREF(f);
        return posix_error();
    }
    /* We now know we will succeed, so initialize the file object. */
    ((PyFileObject *)f)->f_fp = fp;
    PyFile_SetBufSize(f, bufsize);
    return f;
}

PyDoc_STRVAR_remove(posix_isatty__doc__,
"isatty(fd) -> bool\n\n\
Return True if the file descriptor 'fd' is an open file descriptor\n\
connected to the slave end of a terminal.");

static PyObject *
posix_isatty(PyObject *self, PyObject *args)
{
    int fd;
    if (!PyArg_ParseTuple(args, "i:isatty", &fd))
        return NULL;
    if (!_PyVerify_fd(fd))
        return PyBool_FromLong(0);
    return PyBool_FromLong(isatty(fd));
}

#ifdef HAVE_PIPE
PyDoc_STRVAR_remove(posix_pipe__doc__,
"pipe() -> (read_end, write_end)\n\n\
Create a pipe.");

static PyObject *
posix_pipe(PyObject *self, PyObject *noargs)
{
    int fds[2];
    int res;
    Py_BEGIN_ALLOW_THREADS
    res = pipe(fds);
    Py_END_ALLOW_THREADS
    if (res != 0)
        return posix_error();
    return Py_BuildValue("(ii)", fds[0], fds[1]);
}
#endif  /* HAVE_PIPE */


#ifdef HAVE_MKFIFO
PyDoc_STRVAR_remove(posix_mkfifo__doc__,
"mkfifo(filename [, mode=0666])\n\n\
Create a FIFO (a POSIX named pipe).");

static PyObject *
posix_mkfifo(PyObject *self, PyObject *args)
{
    char *filename;
    int mode = 0666;
    int res;
    if (!PyArg_ParseTuple(args, "s|i:mkfifo", &filename, &mode))
        return NULL;
    Py_BEGIN_ALLOW_THREADS
    res = mkfifo(filename, mode);
    Py_END_ALLOW_THREADS
    if (res < 0)
        return posix_error();
    Py_INCREF(Py_None);
    return Py_None;
}
#endif

#ifdef HAVE_PUTENV
PyDoc_STRVAR_remove(posix_putenv__doc__,
"putenv(key, value)\n\n\
Change or add an environment variable.");

/* Save putenv() parameters as values here, so we can collect them when they
 * get re-set with another call for the same key. */
static PyObject *posix_putenv_garbage;

static PyObject *
posix_putenv(PyObject *self, PyObject *args)
{
    char *s1, *s2;
    char *newenv;
    PyObject *newstr;
    size_t len;

    if (!PyArg_ParseTuple(args, "ss:putenv", &s1, &s2))
        return NULL;

    /* XXX This can leak memory -- not easy to fix :-( */
    len = strlen(s1) + strlen(s2) + 2;
    /* len includes space for a trailing \0; the size arg to
       PyString_FromStringAndSize does not count that */
    newstr = PyString_FromStringAndSize(NULL, (int)len - 1);
    if (newstr == NULL)
        return PyErr_NoMemory();
    newenv = PyString_AS_STRING(newstr);
    PyOS_snprintf(newenv, len, "%s=%s", s1, s2);
    if (putenv(newenv)) {
        Py_DECREF(newstr);
        posix_error();
        return NULL;
    }
    /* Install the first arg and newstr in posix_putenv_garbage;
     * this will cause previous value to be collected.  This has to
     * happen after the real putenv() call because the old value
     * was still accessible until then. */
    if (PyDict_SetItem(posix_putenv_garbage,
                       PyTuple_GET_ITEM(args, 0), newstr)) {
        /* really not much we can do; just leak */
        PyErr_Clear();
    }
    else {
        Py_DECREF(newstr);
    }

    Py_INCREF(Py_None);
    return Py_None;
}
#endif /* putenv */

#ifdef HAVE_UNSETENV
PyDoc_STRVAR_remove(posix_unsetenv__doc__,
"unsetenv(key)\n\n\
Delete an environment variable.");

static PyObject *
posix_unsetenv(PyObject *self, PyObject *args)
{
    char *s1;
#ifndef HAVE_BROKEN_UNSETENV
    int err;
#endif

    if (!PyArg_ParseTuple(args, "s:unsetenv", &s1))
        return NULL;

#ifdef HAVE_BROKEN_UNSETENV
    unsetenv(s1);
#else
    err = unsetenv(s1);
    if (err)
        return posix_error();
#endif

    /* Remove the key from posix_putenv_garbage;
     * this will cause it to be collected.  This has to
     * happen after the real unsetenv() call because the
     * old value was still accessible until then.
     */
    if (PyDict_DelItem(posix_putenv_garbage,
                       PyTuple_GET_ITEM(args, 0))) {
        /* really not much we can do; just leak */
        PyErr_Clear();
    }

    Py_INCREF(Py_None);
    return Py_None;
}
#endif /* unsetenv */

PyDoc_STRVAR_remove(posix_strerror__doc__,
"strerror(code) -> string\n\n\
Translate an error code to a message string.");

static PyObject *
posix_strerror(PyObject *self, PyObject *args)
{
    int code;
    char *message;
    if (!PyArg_ParseTuple(args, "i:strerror", &code))
        return NULL;
    message = strerror(code);
    if (message == NULL) {
        PyErr_SetString(PyExc_ValueError,
                        "strerror() argument out of range");
        return NULL;
    }
    return PyString_FromString(message);
}


#ifdef HAVE_SYS_WAIT_H

#ifdef WCOREDUMP
PyDoc_STRVAR_remove(posix_WCOREDUMP__doc__,
"WCOREDUMP(status) -> bool\n\n\
Return True if the process returning 'status' was dumped to a core file.");

static PyObject *
posix_WCOREDUMP(PyObject *self, PyObject *args)
{
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:WCOREDUMP", &WAIT_STATUS_INT(status)))
        return NULL;

    return PyBool_FromLong(WCOREDUMP(status));
}
#endif /* WCOREDUMP */

#ifdef WIFCONTINUED
PyDoc_STRVAR_remove(posix_WIFCONTINUED__doc__,
"WIFCONTINUED(status) -> bool\n\n\
Return True if the process returning 'status' was continued from a\n\
job control stop.");

static PyObject *
posix_WIFCONTINUED(PyObject *self, PyObject *args)
{
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:WCONTINUED", &WAIT_STATUS_INT(status)))
        return NULL;

    return PyBool_FromLong(WIFCONTINUED(status));
}
#endif /* WIFCONTINUED */

#ifdef WIFSTOPPED
PyDoc_STRVAR_remove(posix_WIFSTOPPED__doc__,
"WIFSTOPPED(status) -> bool\n\n\
Return True if the process returning 'status' was stopped.");

static PyObject *
posix_WIFSTOPPED(PyObject *self, PyObject *args)
{
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:WIFSTOPPED", &WAIT_STATUS_INT(status)))
        return NULL;

    return PyBool_FromLong(WIFSTOPPED(status));
}
#endif /* WIFSTOPPED */

#ifdef WIFSIGNALED
PyDoc_STRVAR_remove(posix_WIFSIGNALED__doc__,
"WIFSIGNALED(status) -> bool\n\n\
Return True if the process returning 'status' was terminated by a signal.");

static PyObject *
posix_WIFSIGNALED(PyObject *self, PyObject *args)
{
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:WIFSIGNALED", &WAIT_STATUS_INT(status)))
        return NULL;

    return PyBool_FromLong(WIFSIGNALED(status));
}
#endif /* WIFSIGNALED */

#ifdef WIFEXITED
PyDoc_STRVAR_remove(posix_WIFEXITED__doc__,
"WIFEXITED(status) -> bool\n\n\
Return true if the process returning 'status' exited using the exit()\n\
system call.");

static PyObject *
posix_WIFEXITED(PyObject *self, PyObject *args)
{
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:WIFEXITED", &WAIT_STATUS_INT(status)))
        return NULL;

    return PyBool_FromLong(WIFEXITED(status));
}
#endif /* WIFEXITED */

#ifdef WEXITSTATUS
PyDoc_STRVAR_remove(posix_WEXITSTATUS__doc__,
"WEXITSTATUS(status) -> integer\n\n\
Return the process return code from 'status'.");

static PyObject *
posix_WEXITSTATUS(PyObject *self, PyObject *args)
{
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:WEXITSTATUS", &WAIT_STATUS_INT(status)))
        return NULL;

    return Py_BuildValue("i", WEXITSTATUS(status));
}
#endif /* WEXITSTATUS */

#ifdef WTERMSIG
PyDoc_STRVAR_remove(posix_WTERMSIG__doc__,
"WTERMSIG(status) -> integer\n\n\
Return the signal that terminated the process that provided the 'status'\n\
value.");

static PyObject *
posix_WTERMSIG(PyObject *self, PyObject *args)
{
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:WTERMSIG", &WAIT_STATUS_INT(status)))
        return NULL;

    return Py_BuildValue("i", WTERMSIG(status));
}
#endif /* WTERMSIG */

#ifdef WSTOPSIG
PyDoc_STRVAR_remove(posix_WSTOPSIG__doc__,
"WSTOPSIG(status) -> integer\n\n\
Return the signal that stopped the process that provided\n\
the 'status' value.");

static PyObject *
posix_WSTOPSIG(PyObject *self, PyObject *args)
{
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;

    if (!PyArg_ParseTuple(args, "i:WSTOPSIG", &WAIT_STATUS_INT(status)))
        return NULL;

    return Py_BuildValue("i", WSTOPSIG(status));
}
#endif /* WSTOPSIG */

#endif /* HAVE_SYS_WAIT_H */

#include "Python-2.7.13/Modules/posixmodule.c/posix_methods.def"

static int
ins(PyObject *module, char *symbol, long value)
{
    return PyModule_AddIntConstant(module, symbol, value);
}

static int
all_ins(PyObject *d)
{
  /* Oil PATCH: X_OK -> X_OK_ to avoid name conflict with macro after
   * translation */

#ifdef F_OK
    if (ins(d, "F_OK_", (long)F_OK)) return -1;
#endif
#ifdef R_OK
    if (ins(d, "R_OK_", (long)R_OK)) return -1;
#endif
#ifdef W_OK
    if (ins(d, "W_OK_", (long)W_OK)) return -1;
#endif
#ifdef X_OK
    if (ins(d, "X_OK_", (long)X_OK)) return -1;
#endif
#ifdef NGROUPS_MAX
    if (ins(d, "NGROUPS_MAX", (long)NGROUPS_MAX)) return -1;
#endif
#ifdef TMP_MAX
    if (ins(d, "TMP_MAX", (long)TMP_MAX)) return -1;
#endif
#ifdef WCONTINUED
    if (ins(d, "WCONTINUED", (long)WCONTINUED)) return -1;
#endif
#ifdef WNOHANG
    if (ins(d, "WNOHANG", (long)WNOHANG)) return -1;
#endif
#ifdef WUNTRACED
    if (ins(d, "WUNTRACED", (long)WUNTRACED)) return -1;
#endif
#ifdef O_RDONLY
    if (ins(d, "O_RDONLY", (long)O_RDONLY)) return -1;
#endif
#ifdef O_WRONLY
    if (ins(d, "O_WRONLY", (long)O_WRONLY)) return -1;
#endif
#ifdef O_RDWR
    if (ins(d, "O_RDWR", (long)O_RDWR)) return -1;
#endif
#ifdef O_NDELAY
    if (ins(d, "O_NDELAY", (long)O_NDELAY)) return -1;
#endif
#ifdef O_NONBLOCK
    if (ins(d, "O_NONBLOCK", (long)O_NONBLOCK)) return -1;
#endif
#ifdef O_APPEND
    if (ins(d, "O_APPEND", (long)O_APPEND)) return -1;
#endif
#ifdef O_DSYNC
    if (ins(d, "O_DSYNC", (long)O_DSYNC)) return -1;
#endif
#ifdef O_RSYNC
    if (ins(d, "O_RSYNC", (long)O_RSYNC)) return -1;
#endif
#ifdef O_SYNC
    if (ins(d, "O_SYNC", (long)O_SYNC)) return -1;
#endif
#ifdef O_NOCTTY
    if (ins(d, "O_NOCTTY", (long)O_NOCTTY)) return -1;
#endif
#ifdef O_CREAT
    if (ins(d, "O_CREAT", (long)O_CREAT)) return -1;
#endif
#ifdef O_EXCL
    if (ins(d, "O_EXCL", (long)O_EXCL)) return -1;
#endif
#ifdef O_TRUNC
    if (ins(d, "O_TRUNC", (long)O_TRUNC)) return -1;
#endif
#ifdef O_BINARY
    if (ins(d, "O_BINARY", (long)O_BINARY)) return -1;
#endif
#ifdef O_TEXT
    if (ins(d, "O_TEXT", (long)O_TEXT)) return -1;
#endif
#ifdef O_LARGEFILE
    if (ins(d, "O_LARGEFILE", (long)O_LARGEFILE)) return -1;
#endif
#ifdef O_SHLOCK
    if (ins(d, "O_SHLOCK", (long)O_SHLOCK)) return -1;
#endif
#ifdef O_EXLOCK
    if (ins(d, "O_EXLOCK", (long)O_EXLOCK)) return -1;
#endif

    return 0;
}

#define INITFUNC initposix_
#define MODNAME "posix_"

PyMODINIT_FUNC
INITFUNC(void)
{
    PyObject *m, *v;

    m = Py_InitModule3(MODNAME,
                       posix_methods,
                       posix__doc__);
    if (m == NULL)
        return;

    /* Initialize environ dictionary */
    v = convertenviron();
    Py_XINCREF(v);
    if (v == NULL || PyModule_AddObject(m, "environ", v) != 0)
        return;
    Py_DECREF(v);

    if (all_ins(m))
        return;

    /* OVM_MAIN: We might want to redefine OSError as IOError like Python 3 ?
     * */
    Py_INCREF(PyExc_OSError);
    PyModule_AddObject(m, "error", PyExc_OSError);

#ifdef HAVE_PUTENV
    if (posix_putenv_garbage == NULL)
        posix_putenv_garbage = PyDict_New();
#endif

    if (!initialized) {
        stat_result_desc.name = MODNAME ".stat_result";
        stat_result_desc.fields[7].name = PyStructSequence_UnnamedField;
        stat_result_desc.fields[8].name = PyStructSequence_UnnamedField;
        stat_result_desc.fields[9].name = PyStructSequence_UnnamedField;
        PyStructSequence_InitType(&StatResultType, &stat_result_desc);
        structseq_new = StatResultType.tp_new;
        StatResultType.tp_new = statresult_new;

#ifdef NEED_TICKS_PER_SECOND
#  if defined(HAVE_SYSCONF) && defined(_SC_CLK_TCK)
        ticks_per_second = sysconf(_SC_CLK_TCK);
#  elif defined(HZ)
        ticks_per_second = HZ;
#  else
        ticks_per_second = 60; /* magic fallback value; may be bogus */
#  endif
#endif
    }
    Py_INCREF((PyObject*) &StatResultType);
    PyModule_AddObject(m, "stat_result", (PyObject*) &StatResultType);
    initialized = 1;
}

#ifdef __cplusplus
}
#endif

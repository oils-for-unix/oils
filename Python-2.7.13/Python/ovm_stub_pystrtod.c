#include <Python.h>

double
PyOS_string_to_double(const char *s,
                      char **endptr,
                      PyObject *overflow_exception)
{
    /* not implemented! */
    fprintf(stderr, "OVM: PyOS_string_to_double()\n");
    assert(0);
}

PyAPI_FUNC(char *) PyOS_double_to_string(double val,
                                         char format_code,
                                         int precision,
                                         int flags,
                                         int *type)
{
    /* not implemented! */
    fprintf(stderr, "OVM: PyOS_double_to_string()\n");
    assert(0);
}

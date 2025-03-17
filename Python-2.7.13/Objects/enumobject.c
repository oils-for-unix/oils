/* enumerate object */

#include "Python.h"

typedef struct {
    PyObject_HEAD
    Py_ssize_t en_index;           /* current index of enumeration */
    PyObject* en_sit;          /* secondary iterator of enumeration */
    PyObject* en_result;           /* result tuple  */
    PyObject* en_longindex;        /* index for sequences >= PY_SSIZE_T_MAX */
} enumobject;

static PyObject *
enum_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    enumobject *en;
    PyObject *seq = NULL;
    PyObject *start = NULL;
    static char *kwlist[] = {"sequence", "start", 0};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O:enumerate", kwlist,
                                     &seq, &start))
        return NULL;

    en = (enumobject *)type->tp_alloc(type, 0);
    if (en == NULL)
        return NULL;
    if (start != NULL) {
        start = PyNumber_Index(start);
        if (start == NULL) {
            Py_DECREF(en);
            return NULL;
        }
        assert(PyInt_Check(start) || PyLong_Check(start));
        en->en_index = PyInt_AsSsize_t(start);
        if (en->en_index == -1 && PyErr_Occurred()) {
            PyErr_Clear();
            en->en_index = PY_SSIZE_T_MAX;
            en->en_longindex = start;
        } else {
            en->en_longindex = NULL;
            Py_DECREF(start);
        }
    } else {
        en->en_index = 0;
        en->en_longindex = NULL;
    }
    en->en_sit = PyObject_GetIter(seq);
    if (en->en_sit == NULL) {
        Py_DECREF(en);
        return NULL;
    }
    en->en_result = PyTuple_Pack(2, Py_None, Py_None);
    if (en->en_result == NULL) {
        Py_DECREF(en);
        return NULL;
    }
    return (PyObject *)en;
}

static void
enum_dealloc(enumobject *en)
{
    PyObject_GC_UnTrack(en);
    Py_XDECREF(en->en_sit);
    Py_XDECREF(en->en_result);
    Py_XDECREF(en->en_longindex);
    Py_TYPE(en)->tp_free(en);
}

static int
enum_traverse(enumobject *en, visitproc visit, void *arg)
{
    Py_VISIT(en->en_sit);
    Py_VISIT(en->en_result);
    Py_VISIT(en->en_longindex);
    return 0;
}

static PyObject *
enum_next_long(enumobject *en, PyObject* next_item)
{
    static PyObject *one = NULL;
    PyObject *result = en->en_result;
    PyObject *next_index;
    PyObject *stepped_up;

    if (en->en_longindex == NULL) {
        en->en_longindex = PyInt_FromSsize_t(PY_SSIZE_T_MAX);
        if (en->en_longindex == NULL)
            return NULL;
    }
    if (one == NULL) {
        one = PyInt_FromLong(1);
        if (one == NULL)
            return NULL;
    }
    next_index = en->en_longindex;
    assert(next_index != NULL);
    stepped_up = PyNumber_Add(next_index, one);
    if (stepped_up == NULL)
        return NULL;
    en->en_longindex = stepped_up;

    if (result->ob_refcnt == 1) {
        Py_INCREF(result);
        Py_DECREF(PyTuple_GET_ITEM(result, 0));
        Py_DECREF(PyTuple_GET_ITEM(result, 1));
    } else {
        result = PyTuple_New(2);
        if (result == NULL) {
            Py_DECREF(next_index);
            Py_DECREF(next_item);
            return NULL;
        }
    }
    PyTuple_SET_ITEM(result, 0, next_index);
    PyTuple_SET_ITEM(result, 1, next_item);
    return result;
}

static PyObject *
enum_next(enumobject *en)
{
    PyObject *next_index;
    PyObject *next_item;
    PyObject *result = en->en_result;
    PyObject *it = en->en_sit;

    next_item = (*Py_TYPE(it)->tp_iternext)(it);
    if (next_item == NULL)
        return NULL;

    if (en->en_index == PY_SSIZE_T_MAX)
        return enum_next_long(en, next_item);

    next_index = PyInt_FromSsize_t(en->en_index);
    if (next_index == NULL) {
        Py_DECREF(next_item);
        return NULL;
    }
    en->en_index++;

    if (result->ob_refcnt == 1) {
        Py_INCREF(result);
        Py_DECREF(PyTuple_GET_ITEM(result, 0));
        Py_DECREF(PyTuple_GET_ITEM(result, 1));
    } else {
        result = PyTuple_New(2);
        if (result == NULL) {
            Py_DECREF(next_index);
            Py_DECREF(next_item);
            return NULL;
        }
    }
    PyTuple_SET_ITEM(result, 0, next_index);
    PyTuple_SET_ITEM(result, 1, next_item);
    return result;
}

PyDoc_STRVAR(enum_doc,
"enumerate(iterable[, start]) -> iterator for index, value of iterable\n"
"\n"
"Return an enumerate object.  iterable must be another object that supports\n"
"iteration.  The enumerate object yields pairs containing a count (from\n"
"start, which defaults to zero) and a value yielded by the iterable argument.\n"
"enumerate is useful for obtaining an indexed list:\n"
"    (0, seq[0]), (1, seq[1]), (2, seq[2]), ...");

PyTypeObject PyEnum_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "enumerate",                    /* tp_name */
    sizeof(enumobject),             /* tp_basicsize */
    0,                              /* tp_itemsize */
    /* methods */
    (destructor)enum_dealloc,       /* tp_dealloc */
    0,                              /* tp_print */
    0,                              /* tp_getattr */
    0,                              /* tp_setattr */
    0,                              /* tp_compare */
    0,                              /* tp_repr */
    0,                              /* tp_as_number */
    0,                              /* tp_as_sequence */
    0,                              /* tp_as_mapping */
    0,                              /* tp_hash */
    0,                              /* tp_call */
    0,                              /* tp_str */
    PyObject_GenericGetAttr,        /* tp_getattro */
    0,                              /* tp_setattro */
    0,                              /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
        Py_TPFLAGS_BASETYPE,    /* tp_flags */
    enum_doc,                       /* tp_doc */
    (traverseproc)enum_traverse,    /* tp_traverse */
    0,                              /* tp_clear */
    0,                              /* tp_richcompare */
    0,                              /* tp_weaklistoffset */
    PyObject_SelfIter,                  /* tp_iter */
    (iternextfunc)enum_next,        /* tp_iternext */
    0,                              /* tp_methods */
    0,                              /* tp_members */
    0,                              /* tp_getset */
    0,                              /* tp_base */
    0,                              /* tp_dict */
    0,                              /* tp_descr_get */
    0,                              /* tp_descr_set */
    0,                              /* tp_dictoffset */
    0,                              /* tp_init */
    PyType_GenericAlloc,            /* tp_alloc */
    enum_new,                       /* tp_new */
    PyObject_GC_Del,                /* tp_free */
};

/* Reversed Object ***************************************************************/

typedef struct {
    PyObject_HEAD
    Py_ssize_t      index;
    PyObject* seq;
} reversedobject;

static PyObject *
reversed_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    Py_ssize_t n;
    PyObject *seq, *reversed_meth;
    static PyObject *reversed_cache = NULL;
    reversedobject *ro;

    if (type == &PyReversed_Type && !_PyArg_NoKeywords("reversed()", kwds))
        return NULL;

    if (!PyArg_UnpackTuple(args, "reversed", 1, 1, &seq) )
        return NULL;

    if (PyInstance_Check(seq)) {
        reversed_meth = PyObject_GetAttrString(seq, "__reversed__");
        if (reversed_meth == NULL) {
            if (PyErr_ExceptionMatches(PyExc_AttributeError))
                PyErr_Clear();
            else
                return NULL;
        }
    }
    else {
        reversed_meth = _PyObject_LookupSpecial(seq, "__reversed__",
                                                &reversed_cache);
        if (reversed_meth == NULL && PyErr_Occurred())
            return NULL;
    }
    if (reversed_meth != NULL) {
        PyObject *res = PyObject_CallFunctionObjArgs(reversed_meth, NULL);
        Py_DECREF(reversed_meth);
        return res;
    }

    if (!PySequence_Check(seq)) {
        PyErr_SetString(PyExc_TypeError,
                        "argument to reversed() must be a sequence");
        return NULL;
    }

    n = PySequence_Size(seq);
    if (n == -1)
        return NULL;

    ro = (reversedobject *)type->tp_alloc(type, 0);
    if (ro == NULL)
        return NULL;

    ro->index = n-1;
    Py_INCREF(seq);
    ro->seq = seq;
    return (PyObject *)ro;
}

static void
reversed_dealloc(reversedobject *ro)
{
    PyObject_GC_UnTrack(ro);
    Py_XDECREF(ro->seq);
    Py_TYPE(ro)->tp_free(ro);
}

static int
reversed_traverse(reversedobject *ro, visitproc visit, void *arg)
{
    Py_VISIT(ro->seq);
    return 0;
}

static PyObject *
reversed_next(reversedobject *ro)
{
    PyObject *item;
    Py_ssize_t index = ro->index;

    if (index >= 0) {
        item = PySequence_GetItem(ro->seq, index);
        if (item != NULL) {
            ro->index--;
            return item;
        }
        if (PyErr_ExceptionMatches(PyExc_IndexError) ||
            PyErr_ExceptionMatches(PyExc_StopIteration))
            PyErr_Clear();
    }
    ro->index = -1;
    Py_CLEAR(ro->seq);
    return NULL;
}

PyDoc_STRVAR(reversed_doc,
"reversed(sequence) -> reverse iterator over values of the sequence\n"
"\n"
"Return a reverse iterator");

static PyObject *
reversed_len(reversedobject *ro)
{
    Py_ssize_t position, seqsize;

    if (ro->seq == NULL)
        return PyInt_FromLong(0);
    seqsize = PySequence_Size(ro->seq);
    if (seqsize == -1)
        return NULL;
    position = ro->index + 1;
    return PyInt_FromSsize_t((seqsize < position)  ?  0  :  position);
}

PyDoc_STRVAR(length_hint_doc, "Private method returning an estimate of len(list(it)).");

static PyMethodDef reversediter_methods[] = {
    {"__length_hint__", (PyCFunction)reversed_len, METH_NOARGS, length_hint_doc},
    {NULL,              NULL}           /* sentinel */
};

PyTypeObject PyReversed_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "reversed",                     /* tp_name */
    sizeof(reversedobject),         /* tp_basicsize */
    0,                              /* tp_itemsize */
    /* methods */
    (destructor)reversed_dealloc,   /* tp_dealloc */
    0,                              /* tp_print */
    0,                              /* tp_getattr */
    0,                              /* tp_setattr */
    0,                              /* tp_compare */
    0,                              /* tp_repr */
    0,                              /* tp_as_number */
    0,                                  /* tp_as_sequence */
    0,                              /* tp_as_mapping */
    0,                              /* tp_hash */
    0,                              /* tp_call */
    0,                              /* tp_str */
    PyObject_GenericGetAttr,        /* tp_getattro */
    0,                              /* tp_setattro */
    0,                              /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
        Py_TPFLAGS_BASETYPE,    /* tp_flags */
    reversed_doc,                   /* tp_doc */
    (traverseproc)reversed_traverse,/* tp_traverse */
    0,                              /* tp_clear */
    0,                              /* tp_richcompare */
    0,                              /* tp_weaklistoffset */
    PyObject_SelfIter,                  /* tp_iter */
    (iternextfunc)reversed_next,    /* tp_iternext */
    reversediter_methods,               /* tp_methods */
    0,                              /* tp_members */
    0,                              /* tp_getset */
    0,                              /* tp_base */
    0,                              /* tp_dict */
    0,                              /* tp_descr_get */
    0,                              /* tp_descr_set */
    0,                              /* tp_dictoffset */
    0,                              /* tp_init */
    PyType_GenericAlloc,            /* tp_alloc */
    reversed_new,                   /* tp_new */
    PyObject_GC_Del,                /* tp_free */
};

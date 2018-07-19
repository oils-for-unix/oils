"""
Convert a Python2 code object (actually a subset of what's
possible) to a sequence of C definitions suitable for the
stripped-down experimental OPy interpreter.
Usage like: python cstruct_from_code.py _tmp/fibonacci.pyc
"""

import marshal
import json
import sys

def dump_code(code):
    print """\
typedef unsigned char uint8;
typedef long long int64;

typedef struct {
    uint8 *co_code;
    int64 *co_consts;
    const char **co_names;
    unsigned stacksize;
} Code;

"""
    # TODO fill to 80 columns
    print 'static uint8 co_code[] = { '
    print '  ' + ', '.join('%d' % ord(b) for b in bytes(code.co_code))
    print '};'
    print 
    print 'static const char *co_names[] = { '
    print '  ' + ', '.join(json.dumps(s)  # XXX hack for C string encoding
                           for s in code.co_names)
    print '};'
    print 
    print 'static int64 co_consts[] = { '
    print '  ' + ', '.join(dump_constant(c)
                           for c in code.co_consts)
    print '};'
    print 
    print 'static Code code = {'
    print '  co_code,'
    print '  co_consts,'
    print '  co_names,'
    print '  %d,  // stacksize' % code.co_stacksize
    print '};'

def dump_constant(x):
    if isinstance(x, int):
        return '%d' % x
    else:
        return '0'   # XXX super hack
#    else:
#        assert False, "Unknown constant type: %r" % (x,)

filename = sys.argv[1]
if filename.endswith('.py'):
    # use CPython compiler just for the moment
    with open(filename) as f:
        text = f.read()
        code = compile(text, filename, 'exec')
else:
    # use a .pyc file from anywhere
    with open(filename) as f:
        contents = f.read()
        code = marshal.loads(contents[8:])  # skip over the header to the marshalled code object

dump_code(code)

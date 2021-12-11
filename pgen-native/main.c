#include "python_grammar.h"
#include "parsetok.h"
#include "tokenizer.h"


static const char *tests[] = {
    "1",
    "3 * 2 + 1",
    "1 + 2 * 3",
    "foo",
    "foo()",
    "foo(1)",
    "def double(x): return x * 2",
    "lambda x: x * 2",
    // XXX: don't touch this
    NULL
};


static void parse_one(const char *str) {
    perrdetail err;

    // XXX: Fix this memory leak
    // XXX: inspect the error return value
    PyNode_ListTree(
	PyParser_ParseString(
	    str,
	    &python_grammar,
	    eval_input,
	    &err));

    fprintf(stdout, "\n");
}


int main (int argc, char **argv) {
    for (const char **i = tests; *i != NULL; i++) {
	// XXX: handle errors
	parse_one(*i);
    }
    return 0;
}

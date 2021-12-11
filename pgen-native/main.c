#include "python_grammar.h"
#include "parsetok.h"
#include "tokenizer.h"


static const char *test_string = "3 * 2 + 1";


int main (int argc, char **argv) {
  perrdetail err;

  // XXX: Ignoring this memory leak for now;
  PyNode_ListTree(
	  PyParser_ParseString(
		  test_string,
		  &python_grammar,
		  eval_input,
		  &err));

 exit:
  return 0;

 err:
  return -1;
}

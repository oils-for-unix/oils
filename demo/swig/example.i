/* File: example.i */
%module example

%{
#define SWIG_FILE_WITH_INIT
#include "example.h"
%}

/*
 * Repeat the prototypes of wrapped functions here
 * Namespaces are required, but don't seem to affect the generated Python
 * extension.
 */
namespace fanos {

int fact(int n);
int add(int x, int y);
void send(int fd, Str* s);

}

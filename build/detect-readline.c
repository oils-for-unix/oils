/* 'info readline' shows an example with these three headers */

#include <stdio.h>  /* readline needs this, issue #21 */
#include <readline/readline.h>
#include <readline/history.h>

int main(void) {
  char *line = readline("");
  return 0;
}


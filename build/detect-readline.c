/* 'info readline' shows an example with these three headers */

/* clang-format off */
#include <stdio.h> /* readline needs this, issue #21 */
#include <readline/readline.h>
#include <readline/history.h>
/* clang-format on */

int main(void) {
  char *line = readline("");

  return 0;
}

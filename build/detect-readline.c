/* 'info readline' shows an example with these three headers */

#include <stdio.h>  /* readline needs this, issue #21 */
#include <readline/readline.h>
#include <readline/history.h>

static int test_event_hook(void) {
  return 0;
}

int main(void) {
  char *line = readline("");
  rl_event_hook = test_event_hook;  // ensure readline version is recent enough
  return 0;
}

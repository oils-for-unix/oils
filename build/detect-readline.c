/* 'info readline' shows an example with these three headers */

#include <stdio.h>  /* readline needs this, issue #21 */
#include <readline/readline.h>
#include <readline/history.h>

static int test_event_hook(void) {
  return 0;
}

int main(void) {
  char *line = readline("");

  /* Ensure readline version is recent enough.
     This line will break the build otherwise: https://git.io/vhZ3B */
  rl_event_hook = test_event_hook;

  /* TODO: We could also test other functions we use, like rl_resize_terminal()
   */

  return 0;
}

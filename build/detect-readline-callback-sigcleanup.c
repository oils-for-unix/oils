/* clang-format off */
#include <stdio.h>
#include <readline/readline.h>
#include <readline/history.h>
/* clang-format on */

int main(void) {
  rl_callback_sigcleanup();
  return 0;
}

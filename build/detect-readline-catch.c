/* clang-format off */
#include <stdio.h>
#include <readline/readline.h>
#include <readline/history.h>
/* clang-format on */

int main(void) {
  rl_catch_signals = 0;
  rl_catch_sigwinch = 0;
  return 0;
}

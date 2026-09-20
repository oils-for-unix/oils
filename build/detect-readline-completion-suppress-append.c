/* clang-format off */
#include <stdio.h>
#include <readline/readline.h>
#include <readline/history.h>
/* clang-format on */

int main(void) {
  rl_completion_suppress_append = 0;
  return 0;
}

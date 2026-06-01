/* clang-format off */
#include <stdio.h>
#include <readline/readline.h>
#include <readline/history.h>
/* clang-format on */

int main(void) {
  printf("Address of free_history_entry: %p\n", (void *)free_history_entry);

  return 0;
}

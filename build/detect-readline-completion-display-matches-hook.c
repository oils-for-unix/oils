/* clang-format off */
#include <stdio.h>
#include <readline/readline.h>
#include <readline/history.h>
/* clang-format on */

// The hook type does not match readline in older libedit. And it's still just a
// stub, as of 2026-01:
//
// VFunction *rl_completion_display_matches_hook
//
// https://github.com/NetBSD/src/commit/ef8fd1897c9f08be13bcdc3486d963f1d27dfa7d

void test_hook(char** matches, int num_matches, int max_length) {
  return 0;
}

int main(void) {
  rl_completion_display_matches_hook = test_hook;
}

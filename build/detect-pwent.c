#include <stdio.h>  /* readline needs this, issue #21 */
#include <pwd.h>   // passwd

static int test_event_hook(void) {
  return 0;
}

int main(void) {
  setpwent();
  struct passwd* entry;
  entry = getpwent();
  endpwent();
  return 0;
}

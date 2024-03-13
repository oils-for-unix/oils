#include <pwd.h>   // passwd

int main(void) {
  setpwent();
  struct passwd* entry;
  entry = getpwent();
  endpwent();
  return 0;
}

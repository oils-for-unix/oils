#ifndef DATA_LANG_H
#define DATA_LANG_H

#include "mycpp/runtime.h"

namespace pyj8 {

bool PartIsUtf8(BigStr* s, int start, int end);

void WriteString(BigStr* s, int options, mylib::BufWriter* buf);

}  // namespace pyj8

#endif  // DATA_LANG_H

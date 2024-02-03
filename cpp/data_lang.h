#ifndef DATA_LANG_H
#define DATA_LANG_H

#include "mycpp/runtime.h"

// Direct dependencies of data_lang/j8_lite
namespace fastfunc {

bool CanOmitQuotes(BigStr* s);

BigStr* J8EncodeString(BigStr* s, int j8_fallback);

BigStr* ShellEncodeString(BigStr* s, int ysh_fallback);

}  // namespace fastfunc

namespace pyj8 {

bool PartIsUtf8(BigStr* s, int start, int end);

void WriteString(BigStr* s, int options, mylib::BufWriter* buf);

}  // namespace pyj8

#endif  // DATA_LANG_H

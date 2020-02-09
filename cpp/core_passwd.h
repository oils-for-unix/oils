// core_passwd.h: Replacement for core/passwd.py

#ifndef CORE_PASSWD_H
#define CORE_PASSWD_H

#include "mylib.h"
#include "syntax_asdl.h"

namespace passwd {

Str* GetHomeDir(syntax_asdl::Token* token);

}  // namespace passwd

#endif  // CORE_PASSWD_H

// myerror.h
//
// Separate from mylib.h because it has a side of effect of #undef errno, which
// can't be undone in general.

#ifndef MYERROR_H
#define MYERROR_H

// Needed for the field below to be valid
// https://stackoverflow.com/questions/14261534/temporarily-overwrite-a-macro-in-c-preprocessor
// 
// TODO: Replace with #prgram with something portable
// I think we just need to rewrite e.errno -> e.errno_ in mycpp.

#pragma push_macro("errno")
#undef errno

// Base class that mycpp generates.
class _OSError {
 public:
  int errno;
};

#pragma pop_macro("errno")

class IOError : public _OSError {};

class OSError : public _OSError {};

#endif  // MYERROR_H

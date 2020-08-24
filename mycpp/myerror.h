// myerror.h
//
// Separate from mylib.h because it has a side of effect of #undef errno, which
// can't be undone in general.

#ifndef MYERROR_H
#define MYERROR_H

// Needed for the field below to be valid
// https://stackoverflow.com/questions/14261534/temporarily-overwrite-a-macro-in-c-preprocessor

#undef errno

class IOError {
 public:
  int errno;
};

class OSError {
 public:
  int errno;
};

#endif  // MYERROR_H

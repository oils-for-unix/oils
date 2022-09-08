// myerror.h
//
// This header defines OSError with an 'errno' field, which Python requires.
// So it must be #included FIRST, before anything that defines the 'errno'
// macro is #included!

#ifndef MYERROR_H
#define MYERROR_H

// Base class that mycpp generates.
class _OSError {
 public:
  explicit _OSError(int err_num) : errno(err_num) {
  }
  int errno;
};

class IOError : public _OSError {
 public:
  explicit IOError(int err_num) : _OSError(err_num) {
  }
};

class OSError : public _OSError {
 public:
  explicit OSError(int err_num) : _OSError(err_num) {
  }
};

#endif  // MYERROR_H

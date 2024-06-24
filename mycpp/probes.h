#ifndef MYCPP_PROBES_H
#define MYCPP_PROBES_H

#include "_build/detected-cpp-config.h"  // for HAVE_SYSTEMTAP_SDT

// Added __has_include() for running unit tests with cc -m32 (32 bit build),
// which finds some issues
// ./configure probes without -m32 and sets HAVE_SYSTEMTAP_SDT
// Technically this is C++ 17, but it seems to work with -std=c++11
#if HAVE_SYSTEMTAP_SDT && __has_include(<sys/sdt.h>)
  #include <sys/sdt.h>
#else
  #define DTRACE_PROBE(provider, probe)
  #define DTRACE_PROBE1(provider, probe, parm1)
  #define DTRACE_PROBE2(provider, probe, parm1, parm2)
  #define DTRACE_PROBE3(provider, probe, parm1, parm2, parm3)
  #define DTRACE_PROBE4(provider, probe, parm1, parm2, parm3, parm4)
  #define DTRACE_PROBE5(provider, probe, parm1, parm2, parm3, parm4, parm5)
  #define DTRACE_PROBE6(provider, probe, parm1, parm2, parm3, parm4, parm5, \
                        parm6)
  #define DTRACE_PROBE7(provider, probe, parm1, parm2, parm3, parm4, parm5, \
                        parm6, parm7)
  #define DTRACE_PROBE8(provider, probe, parm1, parm2, parm3, parm4, parm5, \
                        parm6, parm7, parm8)
  #define DTRACE_PROBE9(provider, probe, parm1, parm2, parm3, parm4, parm5, \
                        parm6, parm7, parm8, parm9)
  #define DTRACE_PROBE10(provider, probe, parm1, parm2, parm3, parm4, parm5, \
                         parm6, parm7, parm8, parm9, parm10)
  #define DTRACE_PROBE11(provider, probe, parm1, parm2, parm3, parm4, parm5, \
                         parm6, parm7, parm8, parm9, parm10, parm11)
  #define DTRACE_PROBE12(provider, probe, parm1, parm2, parm3, parm4, parm5, \
                         parm6, parm7, parm8, parm9, parm10, parm11, parm12)
#endif

#endif  // MYCPP_PROBES_H

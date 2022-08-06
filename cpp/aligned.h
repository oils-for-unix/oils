#ifndef ALIGNED_H
#define ALIGNED_H

// I'm not sure why this matters but we get crashes when aligning to 8 bytes.
// That is annoying.
// Example: we get a crash in cpp/frontend_flag_spec.cc
// auto out = new flag_spec::_FlagSpecAndMore();
//
// https://stackoverflow.com/questions/52531695/int128-alignment-segment-fault-with-gcc-o-sse-optimize
constexpr int kMask = alignof(max_align_t) - 1;  // e.g. 15 or 7

// Align returned pointers to the worst case of 8 bytes (64-bit pointers)
inline size_t aligned(size_t n) {
  // https://stackoverflow.com/questions/2022179/c-quick-calculation-of-next-multiple-of-4
  // return (n + 7) & ~7;
  return (n + kMask) & ~kMask;
}

#endif

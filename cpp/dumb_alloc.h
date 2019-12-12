// Dumb Allocator

#ifndef DUMB_ALLOC_H
#define DUMB_ALLOC_H

#include <cstddef>  // size_t

void* dumb_malloc(size_t size) noexcept;
void dumb_free(void* p) noexcept;

namespace dumb_alloc {

void Summarize();

};  // namespace dumb_alloc

#endif  // DUMB_ALLOC_H

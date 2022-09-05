void* Heap::Allocate(int byte_count)
{
  void* Result = calloc(byte_count, 1);
  return Result;
}

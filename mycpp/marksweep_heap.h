#ifndef MARKSWEEP_H
#define MARKSWEEP_H

#include <unordered_set>
#include <vector>

class MarkSweepHeap;  // forward decl for circular dep

class RootSet {
 public:
  explicit RootSet(int num_reserved) {
    roots_.reserve(num_reserved);  // 32 stack frames to start
    for (int i = 0; i < num_reserved; ++i) {
      // construct std::vector for the frame IN PLACE
      roots_.emplace_back();
      // reserving 16 rooted variables per frame.
      roots_.back().reserve(16);
    }
  }

  void PushScope() {
    // Called on function entry

    // Construct more std::vector frames if necessary.  We reuse vectors to
    // avoid constructing one on every function call.

    int num_constructed = roots_.size();
    // equivalent to NumFrames() >= num_constructed
    if (frame_top_ >= num_constructed) {
      roots_.emplace_back();
      roots_.back().reserve(16);

#if 0
      num_constructed = roots_.size();
      log("frame_top_ %d, num_constructed %d", frame_top_, num_constructed);
      assert(frame_top_ + 1 == num_constructed);
#endif
    }

    frame_top_++;
  }

  void PopScope() {
    // Called on function exit

    // Remove all roots owned by the top frame
    // NOT using vector<>::pop() because we are REUSING objects.
    roots_[frame_top_ - 1].clear();
    frame_top_--;
  }

  void AddRoot(Obj* root) {
    // Called when returning a value

    // true because main() has RootsScope(), and doesn't return objects
    assert(frame_top_ > 1);

    // Owned by the frame BELOW
    roots_[frame_top_ - 2].push_back(root);
  }

  int NumFrames() {
    return frame_top_;
  }

  int NumRoots() {
    // Calculate size of root set, for unit tests only.

    int result = 0;
    for (int i = 0; i < frame_top_; ++i) {
      result += roots_[i].size();
    }
    return result;
  }

  void MarkRoots(MarkSweepHeap* heap) {
    // Start of garbage collection.  We have a circular dependency here because
    // I don't want some kind of STL iterator.

    for (int i = 0; i < frame_top_; ++i) {
      const std::vector<Obj*>& frame = roots_[i];
      int n = frame.size();
      for (int j = 0; j < n; ++j) {
        // TODO: add to gray stack
        ;
      }
    }
  }

  // This representation seems weird, but is appropriate since multiple stack
  // frames are "in play" at once.  That is, AddRoot() may mutate root_set_[1]
  // while root_set_[2] is being pushed/popped/modified.
  std::vector<std::vector<Obj*>> roots_;
  int frame_top_ = 0;  // frames 0 to N-1 are valid
};

class MarkSweepHeap {
 public:
  // reserve 32 frames to start
  MarkSweepHeap() : root_set_(32) {
  }

  void Init();  // default threshold
  void Init(int collect_threshold);

  //
  // OLD ROOTING
  //

  void PushRoot(Obj** p) {
    roots_.push_back(p);
  }

  void PopRoot() {
    roots_.pop_back();
  }

  //
  // NEW Return Value Rooting
  //

  // Hopefully this will get inlined away
  void AddRoot(Obj* root) {
    root_set_.AddRoot(root);
    // Make the object a root until the CALLER returns
  }

  void* Allocate(int num_bytes);
  int Collect();

  void MaybePrintReport();
  void Report();

  // TODO(Jesse): This should really be in an 'internal' build
  bool is_initialized_ = true;  // mark/sweep doesn't need to be initialized

  // In number of live objects, since we aren't keeping track of total bytes
  int collect_threshold_;

  // Cumulative stats
  int64_t num_allocated_ = 0;
  int64_t bytes_allocated_ = 0;
  int64_t num_collections_ = 0;
  int max_live_ = 0;  // max # live after a collection

  // current stats
  int num_live_ = 0;
  // Should we keep track of sizes?
  // int64_t bytes_live_ = 0;

  // OLD rooting
  std::vector<Obj**> roots_;

  // NEW rooting
  RootSet root_set_;

  std::vector<void*> live_objs_;
  std::unordered_set<void*> marked_;

 private:
  void MarkObjects(Obj* obj);

  DISALLOW_COPY_AND_ASSIGN(MarkSweepHeap);
};

#endif

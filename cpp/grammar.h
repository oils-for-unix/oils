// cpp/grammar.h: adapted from CPython's grammar.h

#ifndef OIL_GRAMMAR_H
#define OIL_GRAMMAR_H

#include <bitset>
#include <string>
#include <vector>

namespace grammar {

typedef std::bitset<256> bitset_t;

// A label of an arc
struct label {
  int lb_type;
  std::string lb_str;
};

// An arc from one state to another
struct arc {
  int a_lbl;   /* Label of this arc */
  int a_arrow; /* State where this arc goes to */
};

// A state in a DFA
struct state {
  std::vector<arc> s_arc;  // Array of arcs

  // Optional accelerators
  int s_lower;   // Lowest label index
  int s_upper;   // Highest label index
  int *s_accel;  // Accelerator
  int s_accept;  // Nonzero for accepting state
};

// A DFA
struct dfa {
  int d_type;          // Non-terminal this represents
  std::string d_name;  // For printing
  int d_initial;       // Initial state
  std::vector<state> d_state;
  bitset_t d_first;
};

// A grammar
struct grammar {
  std::vector<dfa> g_dfa;
  std::vector<label> g_ll;
  int g_start;  // Start symbol of the grammar
  int g_accel;  // Set if accelerators present
};

}  // namespace grammar

#endif  // OIL_GRAMMAR_H

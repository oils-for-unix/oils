#define SOUFFLE_GENERATOR_VERSION "2.4.1-26-gc7ce22981"
#include "souffle/CompiledSouffle.h"
#include "souffle/SignalHandler.h"
#include "souffle/SouffleInterface.h"
#include "souffle/datastructure/BTree.h"
#include "souffle/io/IOSystem.h"
#include "souffle/utility/MiscUtil.h"
#include <any>
namespace functors {
extern "C" {
}
} //namespace functors
namespace souffle::t_btree_000_iii__0_1_2__110__111 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 3;
using t_tuple = Tuple<RamDomain, 3>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :(0)));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_110(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_110(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iii__0_1_2__110__111 
namespace souffle::t_btree_000_iii__0_1_2__110__111 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[3];
std::copy(ramDomain, ramDomain + 3, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2) {
RamDomain data[3] = {a0,a1,a2};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_110(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_110(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_110(lower,upper,h);
}
range<t_ind_0::iterator> Type::lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_111(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 3 direct b-tree index 0 lex-order [0,1,2]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_iii__0_1_2__110__111 
namespace souffle::t_btree_000_ii__0_1__11__10 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 2;
using t_tuple = Tuple<RamDomain, 2>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :(0));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_0::iterator> lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_ii__0_1__11__10 
namespace souffle::t_btree_000_ii__0_1__11__10 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[2];
std::copy(ramDomain, ramDomain + 2, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1) {
RamDomain data[2] = {a0,a1};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_11(lower,upper,h);
}
range<t_ind_0::iterator> Type::lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_10(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_10(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 2 direct b-tree index 0 lex-order [0,1]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_ii__0_1__11__10 
namespace souffle::t_btree_000_iii__0_2_1__101__111 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 3;
using t_tuple = Tuple<RamDomain, 3>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :(0)));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))|| ((ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_101(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_101(const t_tuple& lower, const t_tuple& upper) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iii__0_2_1__101__111 
namespace souffle::t_btree_000_iii__0_2_1__101__111 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[3];
std::copy(ramDomain, ramDomain + 3, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2) {
RamDomain data[3] = {a0,a1,a2};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_101(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_101(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_101(lower,upper,h);
}
range<t_ind_0::iterator> Type::lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_111(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 3 direct b-tree index 0 lex-order [0,2,1]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_iii__0_2_1__101__111 
namespace souffle::t_btree_000_iii__0_1_2__111 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 3;
using t_tuple = Tuple<RamDomain, 3>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2])) ? -1 : (ramBitCast<RamSigned>(a[2]) > ramBitCast<RamSigned>(b[2])) ? 1 :(0)));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))|| ((ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1])) && ((ramBitCast<RamSigned>(a[2]) < ramBitCast<RamSigned>(b[2]))))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]))&&(ramBitCast<RamSigned>(a[2]) == ramBitCast<RamSigned>(b[2]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1,RamDomain a2);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_iii__0_1_2__111 
namespace souffle::t_btree_000_iii__0_1_2__111 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[3];
std::copy(ramDomain, ramDomain + 3, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1,RamDomain a2) {
RamDomain data[3] = {a0,a1,a2};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_000(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_111(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_111(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 3 direct b-tree index 0 lex-order [0,1,2]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_iii__0_1_2__111 
namespace souffle::t_btree_000_ii__0_1__11 {
using namespace souffle;
struct Type {
static constexpr Relation::arity_type Arity = 2;
using t_tuple = Tuple<RamDomain, 2>;
struct t_comparator_0{
 int operator()(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0])) ? -1 : (ramBitCast<RamSigned>(a[0]) > ramBitCast<RamSigned>(b[0])) ? 1 :((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1])) ? -1 : (ramBitCast<RamSigned>(a[1]) > ramBitCast<RamSigned>(b[1])) ? 1 :(0));
 }
bool less(const t_tuple& a, const t_tuple& b) const {
  return (ramBitCast<RamSigned>(a[0]) < ramBitCast<RamSigned>(b[0]))|| ((ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0])) && ((ramBitCast<RamSigned>(a[1]) < ramBitCast<RamSigned>(b[1]))));
 }
bool equal(const t_tuple& a, const t_tuple& b) const {
return (ramBitCast<RamSigned>(a[0]) == ramBitCast<RamSigned>(b[0]))&&(ramBitCast<RamSigned>(a[1]) == ramBitCast<RamSigned>(b[1]));
 }
};
using t_ind_0 = btree_set<t_tuple,t_comparator_0>;
t_ind_0 ind_0;
using iterator = t_ind_0::iterator;
struct context {
t_ind_0::operation_hints hints_0_lower;
t_ind_0::operation_hints hints_0_upper;
};
context createContext() { return context(); }
bool insert(const t_tuple& t);
bool insert(const t_tuple& t, context& h);
bool insert(const RamDomain* ramDomain);
bool insert(RamDomain a0,RamDomain a1);
bool contains(const t_tuple& t, context& h) const;
bool contains(const t_tuple& t) const;
std::size_t size() const;
iterator find(const t_tuple& t, context& h) const;
iterator find(const t_tuple& t) const;
range<iterator> lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const;
range<iterator> lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */) const;
range<t_ind_0::iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper, context& h) const;
range<t_ind_0::iterator> lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const;
bool empty() const;
std::vector<range<iterator>> partition() const;
void purge();
iterator begin() const;
iterator end() const;
void printStatistics(std::ostream& o) const;
};
} // namespace souffle::t_btree_000_ii__0_1__11 
namespace souffle::t_btree_000_ii__0_1__11 {
using namespace souffle;
using t_ind_0 = Type::t_ind_0;
using iterator = Type::iterator;
using context = Type::context;
bool Type::insert(const t_tuple& t) {
context h;
return insert(t, h);
}
bool Type::insert(const t_tuple& t, context& h) {
if (ind_0.insert(t, h.hints_0_lower)) {
return true;
} else return false;
}
bool Type::insert(const RamDomain* ramDomain) {
RamDomain data[2];
std::copy(ramDomain, ramDomain + 2, data);
const t_tuple& tuple = reinterpret_cast<const t_tuple&>(data);
context h;
return insert(tuple, h);
}
bool Type::insert(RamDomain a0,RamDomain a1) {
RamDomain data[2] = {a0,a1};
return insert(data);
}
bool Type::contains(const t_tuple& t, context& h) const {
return ind_0.contains(t, h.hints_0_lower);
}
bool Type::contains(const t_tuple& t) const {
context h;
return contains(t, h);
}
std::size_t Type::size() const {
return ind_0.size();
}
iterator Type::find(const t_tuple& t, context& h) const {
return ind_0.find(t, h.hints_0_lower);
}
iterator Type::find(const t_tuple& t) const {
context h;
return find(t, h);
}
range<iterator> Type::lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */, context& /* h */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<iterator> Type::lowerUpperRange_00(const t_tuple& /* lower */, const t_tuple& /* upper */) const {
return range<iterator>(ind_0.begin(),ind_0.end());
}
range<t_ind_0::iterator> Type::lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper, context& h) const {
t_comparator_0 comparator;
int cmp = comparator(lower, upper);
if (cmp == 0) {
    auto pos = ind_0.find(lower, h.hints_0_lower);
    auto fin = ind_0.end();
    if (pos != fin) {fin = pos; ++fin;}
    return make_range(pos, fin);
}
if (cmp > 0) {
    return make_range(ind_0.end(), ind_0.end());
}
return make_range(ind_0.lower_bound(lower, h.hints_0_lower), ind_0.upper_bound(upper, h.hints_0_upper));
}
range<t_ind_0::iterator> Type::lowerUpperRange_11(const t_tuple& lower, const t_tuple& upper) const {
context h;
return lowerUpperRange_11(lower,upper,h);
}
bool Type::empty() const {
return ind_0.empty();
}
std::vector<range<iterator>> Type::partition() const {
return ind_0.getChunks(400);
}
void Type::purge() {
ind_0.clear();
}
iterator Type::begin() const {
return ind_0.begin();
}
iterator Type::end() const {
return ind_0.end();
}
void Type::printStatistics(std::ostream& o) const {
o << " arity 2 direct b-tree index 0 lex-order [0,1]\n";
ind_0.printStats(o);
}
} // namespace souffle::t_btree_000_ii__0_1__11 
namespace  souffle {
using namespace souffle;
class Stratum_cf_edge_c2ae152829fd6f1f {
public:
 Stratum_cf_edge_c2ae152829fd6f1f(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__110__111::Type& rel_cf_edge_4931a04c8c74bb72);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iii__0_1_2__110__111::Type* rel_cf_edge_4931a04c8c74bb72;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_cf_edge_c2ae152829fd6f1f::Stratum_cf_edge_c2ae152829fd6f1f(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__110__111::Type& rel_cf_edge_4931a04c8c74bb72):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_cf_edge_4931a04c8c74bb72(&rel_cf_edge_4931a04c8c74bb72){
}

void Stratum_cf_edge_c2ae152829fd6f1f::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx\ty"},{"auxArity","0"},{"fact-dir","."},{"name","cf_edge"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 3, \"params\": [\"f\", \"x\", \"y\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"s:Statement\", \"s:Statement\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_cf_edge_4931a04c8c74bb72);
} catch (std::exception& e) {std::cerr << "Error loading cf_edge data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_cf_path_281344c75720c946 {
public:
 Stratum_cf_path_281344c75720c946(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_delta_cf_path_a939c29cb29cb918,t_btree_000_iii__0_1_2__111::Type& rel_new_cf_path_7c1a0790df10e865,t_btree_000_iii__0_1_2__110__111::Type& rel_cf_edge_4931a04c8c74bb72,t_btree_000_iii__0_1_2__111::Type& rel_cf_path_018f9b04e61e101f);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iii__0_1_2__111::Type* rel_delta_cf_path_a939c29cb29cb918;
t_btree_000_iii__0_1_2__111::Type* rel_new_cf_path_7c1a0790df10e865;
t_btree_000_iii__0_1_2__110__111::Type* rel_cf_edge_4931a04c8c74bb72;
t_btree_000_iii__0_1_2__111::Type* rel_cf_path_018f9b04e61e101f;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_cf_path_281344c75720c946::Stratum_cf_path_281344c75720c946(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_delta_cf_path_a939c29cb29cb918,t_btree_000_iii__0_1_2__111::Type& rel_new_cf_path_7c1a0790df10e865,t_btree_000_iii__0_1_2__110__111::Type& rel_cf_edge_4931a04c8c74bb72,t_btree_000_iii__0_1_2__111::Type& rel_cf_path_018f9b04e61e101f):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_delta_cf_path_a939c29cb29cb918(&rel_delta_cf_path_a939c29cb29cb918),
rel_new_cf_path_7c1a0790df10e865(&rel_new_cf_path_7c1a0790df10e865),
rel_cf_edge_4931a04c8c74bb72(&rel_cf_edge_4931a04c8c74bb72),
rel_cf_path_018f9b04e61e101f(&rel_cf_path_018f9b04e61e101f){
}

void Stratum_cf_path_281344c75720c946::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(cf_path(f,x,y) :- 
   cf_edge(f,x,y).
in file stack_roots.dl [50:1-50:38])_");
if(!(rel_cf_edge_4931a04c8c74bb72->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_cf_edge_4931a04c8c74bb72_op_ctxt,rel_cf_edge_4931a04c8c74bb72->createContext());
CREATE_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt,rel_cf_path_018f9b04e61e101f->createContext());
for(const auto& env0 : *rel_cf_edge_4931a04c8c74bb72) {
Tuple<RamDomain,3> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[2])}};
rel_cf_path_018f9b04e61e101f->insert(tuple,READ_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt));
}
}
();}
[&](){
CREATE_OP_CONTEXT(rel_delta_cf_path_a939c29cb29cb918_op_ctxt,rel_delta_cf_path_a939c29cb29cb918->createContext());
CREATE_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt,rel_cf_path_018f9b04e61e101f->createContext());
for(const auto& env0 : *rel_cf_path_018f9b04e61e101f) {
Tuple<RamDomain,3> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[2])}};
rel_delta_cf_path_a939c29cb29cb918->insert(tuple,READ_OP_CONTEXT(rel_delta_cf_path_a939c29cb29cb918_op_ctxt));
}
}
();auto loop_counter = RamUnsigned(1);
iter = 0;
for(;;) {
signalHandler->setMsg(R"_(cf_path(f,x,y) :- 
   cf_path(f,x,z),
   cf_edge(f,z,y).
in file stack_roots.dl [52:1-52:56])_");
if(!(rel_delta_cf_path_a939c29cb29cb918->empty()) && !(rel_cf_edge_4931a04c8c74bb72->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_cf_path_a939c29cb29cb918_op_ctxt,rel_delta_cf_path_a939c29cb29cb918->createContext());
CREATE_OP_CONTEXT(rel_new_cf_path_7c1a0790df10e865_op_ctxt,rel_new_cf_path_7c1a0790df10e865->createContext());
CREATE_OP_CONTEXT(rel_cf_edge_4931a04c8c74bb72_op_ctxt,rel_cf_edge_4931a04c8c74bb72->createContext());
CREATE_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt,rel_cf_path_018f9b04e61e101f->createContext());
for(const auto& env0 : *rel_delta_cf_path_a939c29cb29cb918) {
auto range = rel_cf_edge_4931a04c8c74bb72->lowerUpperRange_110(Tuple<RamDomain,3>{{ramBitCast(env0[0]), ramBitCast(env0[2]), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,3>{{ramBitCast(env0[0]), ramBitCast(env0[2]), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_cf_edge_4931a04c8c74bb72_op_ctxt));
for(const auto& env1 : range) {
if( !(rel_cf_path_018f9b04e61e101f->contains(Tuple<RamDomain,3>{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env1[2])}},READ_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt)))) {
Tuple<RamDomain,3> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env1[2])}};
rel_new_cf_path_7c1a0790df10e865->insert(tuple,READ_OP_CONTEXT(rel_new_cf_path_7c1a0790df10e865_op_ctxt));
}
}
}
}
();}
if(rel_new_cf_path_7c1a0790df10e865->empty()) break;
[&](){
CREATE_OP_CONTEXT(rel_new_cf_path_7c1a0790df10e865_op_ctxt,rel_new_cf_path_7c1a0790df10e865->createContext());
CREATE_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt,rel_cf_path_018f9b04e61e101f->createContext());
for(const auto& env0 : *rel_new_cf_path_7c1a0790df10e865) {
Tuple<RamDomain,3> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1]),ramBitCast(env0[2])}};
rel_cf_path_018f9b04e61e101f->insert(tuple,READ_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt));
}
}
();std::swap(rel_delta_cf_path_a939c29cb29cb918, rel_new_cf_path_7c1a0790df10e865);
rel_new_cf_path_7c1a0790df10e865->purge();
loop_counter = (ramBitCast<RamUnsigned>(loop_counter) + ramBitCast<RamUnsigned>(RamUnsigned(1)));
iter++;
}
iter = 0;
rel_delta_cf_path_a939c29cb29cb918->purge();
rel_new_cf_path_7c1a0790df10e865->purge();
if (pruneImdtRels) rel_cf_edge_4931a04c8c74bb72->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_collect_77936cd6fddc6c8c {
public:
 Stratum_collect_77936cd6fddc6c8c(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_ii__0_1__11__10::Type& rel_collect_092686b367d9983d);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_ii__0_1__11__10::Type* rel_collect_092686b367d9983d;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_collect_77936cd6fddc6c8c::Stratum_collect_77936cd6fddc6c8c(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_ii__0_1__11__10::Type& rel_collect_092686b367d9983d):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_collect_092686b367d9983d(&rel_collect_092686b367d9983d){
}

void Stratum_collect_77936cd6fddc6c8c::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx"},{"auxArity","0"},{"fact-dir","."},{"name","collect"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"x\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"s:Statement\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_collect_092686b367d9983d);
} catch (std::exception& e) {std::cerr << "Error loading collect data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_def_6f7db9860aa6b531 {
public:
 Stratum_def_6f7db9860aa6b531(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_2_1__101__111::Type& rel_def_a2557aec54a7a800);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iii__0_2_1__101__111::Type* rel_def_a2557aec54a7a800;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_def_6f7db9860aa6b531::Stratum_def_6f7db9860aa6b531(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_2_1__101__111::Type& rel_def_a2557aec54a7a800):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_def_a2557aec54a7a800(&rel_def_a2557aec54a7a800){
}

void Stratum_def_6f7db9860aa6b531::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx\tv"},{"auxArity","0"},{"fact-dir","."},{"name","def"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 3, \"params\": [\"f\", \"x\", \"v\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"s:Statement\", \"s:Var\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_def_a2557aec54a7a800);
} catch (std::exception& e) {std::cerr << "Error loading def data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_root_vars_d910841585fde373 {
public:
 Stratum_root_vars_d910841585fde373(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_cf_path_018f9b04e61e101f,t_btree_000_ii__0_1__11__10::Type& rel_collect_092686b367d9983d,t_btree_000_iii__0_2_1__101__111::Type& rel_def_a2557aec54a7a800,t_btree_000_ii__0_1__11::Type& rel_root_vars_9dd5ee9984886e0d,t_btree_000_iii__0_1_2__111::Type& rel_use_e955e932f22dad4d);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iii__0_1_2__111::Type* rel_cf_path_018f9b04e61e101f;
t_btree_000_ii__0_1__11__10::Type* rel_collect_092686b367d9983d;
t_btree_000_iii__0_2_1__101__111::Type* rel_def_a2557aec54a7a800;
t_btree_000_ii__0_1__11::Type* rel_root_vars_9dd5ee9984886e0d;
t_btree_000_iii__0_1_2__111::Type* rel_use_e955e932f22dad4d;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_root_vars_d910841585fde373::Stratum_root_vars_d910841585fde373(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_cf_path_018f9b04e61e101f,t_btree_000_ii__0_1__11__10::Type& rel_collect_092686b367d9983d,t_btree_000_iii__0_2_1__101__111::Type& rel_def_a2557aec54a7a800,t_btree_000_ii__0_1__11::Type& rel_root_vars_9dd5ee9984886e0d,t_btree_000_iii__0_1_2__111::Type& rel_use_e955e932f22dad4d):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_cf_path_018f9b04e61e101f(&rel_cf_path_018f9b04e61e101f),
rel_collect_092686b367d9983d(&rel_collect_092686b367d9983d),
rel_def_a2557aec54a7a800(&rel_def_a2557aec54a7a800),
rel_root_vars_9dd5ee9984886e0d(&rel_root_vars_9dd5ee9984886e0d),
rel_use_e955e932f22dad4d(&rel_use_e955e932f22dad4d){
}

void Stratum_root_vars_d910841585fde373::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(root_vars(f,v) :- 
   use(f,y,v),
   def(f,x,v),
   collect(f,y),
   cf_path(f,x,y).
in file stack_roots.dl [56:1-56:80])_");
if(!(rel_collect_092686b367d9983d->empty()) && !(rel_def_a2557aec54a7a800->empty()) && !(rel_use_e955e932f22dad4d->empty()) && !(rel_cf_path_018f9b04e61e101f->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt,rel_cf_path_018f9b04e61e101f->createContext());
CREATE_OP_CONTEXT(rel_collect_092686b367d9983d_op_ctxt,rel_collect_092686b367d9983d->createContext());
CREATE_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt,rel_def_a2557aec54a7a800->createContext());
CREATE_OP_CONTEXT(rel_root_vars_9dd5ee9984886e0d_op_ctxt,rel_root_vars_9dd5ee9984886e0d->createContext());
CREATE_OP_CONTEXT(rel_use_e955e932f22dad4d_op_ctxt,rel_use_e955e932f22dad4d->createContext());
for(const auto& env0 : *rel_use_e955e932f22dad4d) {
if( rel_collect_092686b367d9983d->contains(Tuple<RamDomain,2>{{ramBitCast(env0[0]),ramBitCast(env0[1])}},READ_OP_CONTEXT(rel_collect_092686b367d9983d_op_ctxt))) {
auto range = rel_def_a2557aec54a7a800->lowerUpperRange_101(Tuple<RamDomain,3>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[2])}},Tuple<RamDomain,3>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[2])}},READ_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt));
for(const auto& env1 : range) {
if( rel_cf_path_018f9b04e61e101f->contains(Tuple<RamDomain,3>{{ramBitCast(env0[0]),ramBitCast(env1[1]),ramBitCast(env0[1])}},READ_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt))) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[2])}};
rel_root_vars_9dd5ee9984886e0d->insert(tuple,READ_OP_CONTEXT(rel_root_vars_9dd5ee9984886e0d_op_ctxt));
break;
}
}
}
}
}
();}
signalHandler->setMsg(R"_(root_vars(f,v) :- 
   use(f,z,v),
   def(f,x,v),
   collect(f,y),
   cf_path(f,x,y),
   cf_path(f,y,z).
in file stack_roots.dl [57:1-57:98])_");
if(!(rel_collect_092686b367d9983d->empty()) && !(rel_use_e955e932f22dad4d->empty()) && !(rel_cf_path_018f9b04e61e101f->empty()) && !(rel_def_a2557aec54a7a800->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt,rel_cf_path_018f9b04e61e101f->createContext());
CREATE_OP_CONTEXT(rel_collect_092686b367d9983d_op_ctxt,rel_collect_092686b367d9983d->createContext());
CREATE_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt,rel_def_a2557aec54a7a800->createContext());
CREATE_OP_CONTEXT(rel_root_vars_9dd5ee9984886e0d_op_ctxt,rel_root_vars_9dd5ee9984886e0d->createContext());
CREATE_OP_CONTEXT(rel_use_e955e932f22dad4d_op_ctxt,rel_use_e955e932f22dad4d->createContext());
for(const auto& env0 : *rel_use_e955e932f22dad4d) {
auto range = rel_def_a2557aec54a7a800->lowerUpperRange_101(Tuple<RamDomain,3>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MIN_RAM_SIGNED), ramBitCast(env0[2])}},Tuple<RamDomain,3>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MAX_RAM_SIGNED), ramBitCast(env0[2])}},READ_OP_CONTEXT(rel_def_a2557aec54a7a800_op_ctxt));
for(const auto& env1 : range) {
auto range = rel_collect_092686b367d9983d->lowerUpperRange_10(Tuple<RamDomain,2>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,2>{{ramBitCast(env0[0]), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_collect_092686b367d9983d_op_ctxt));
for(const auto& env2 : range) {
if( rel_cf_path_018f9b04e61e101f->contains(Tuple<RamDomain,3>{{ramBitCast(env0[0]),ramBitCast(env2[1]),ramBitCast(env0[1])}},READ_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt)) && rel_cf_path_018f9b04e61e101f->contains(Tuple<RamDomain,3>{{ramBitCast(env0[0]),ramBitCast(env1[1]),ramBitCast(env2[1])}},READ_OP_CONTEXT(rel_cf_path_018f9b04e61e101f_op_ctxt))) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[2])}};
rel_root_vars_9dd5ee9984886e0d->insert(tuple,READ_OP_CONTEXT(rel_root_vars_9dd5ee9984886e0d_op_ctxt));
}
}
}
}
}
();}
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tv"},{"auxArity","0"},{"name","root_vars"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"v\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"s:Var\"]}}"}});
if (outputDirectory == "-"){directiveMap["IO"] = "stdout"; directiveMap["headers"] = "true";}
else if (!outputDirectory.empty()) {directiveMap["output-dir"] = outputDirectory;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_root_vars_9dd5ee9984886e0d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}
if (pruneImdtRels) rel_cf_path_018f9b04e61e101f->purge();
if (pruneImdtRels) rel_collect_092686b367d9983d->purge();
if (pruneImdtRels) rel_def_a2557aec54a7a800->purge();
if (pruneImdtRels) rel_use_e955e932f22dad4d->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_use_f38e4ba456a0cc9a {
public:
 Stratum_use_f38e4ba456a0cc9a(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_use_e955e932f22dad4d);
void run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret);
private:
SymbolTable& symTable;
RecordTable& recordTable;
ConcurrentCache<std::string,std::regex>& regexCache;
bool& pruneImdtRels;
bool& performIO;
SignalHandler*& signalHandler;
std::atomic<std::size_t>& iter;
std::atomic<RamDomain>& ctr;
std::string& inputDirectory;
std::string& outputDirectory;
t_btree_000_iii__0_1_2__111::Type* rel_use_e955e932f22dad4d;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_use_f38e4ba456a0cc9a::Stratum_use_f38e4ba456a0cc9a(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_000_iii__0_1_2__111::Type& rel_use_e955e932f22dad4d):
symTable(symTable),
recordTable(recordTable),
regexCache(regexCache),
pruneImdtRels(pruneImdtRels),
performIO(performIO),
signalHandler(signalHandler),
iter(iter),
ctr(ctr),
inputDirectory(inputDirectory),
outputDirectory(outputDirectory),
rel_use_e955e932f22dad4d(&rel_use_e955e932f22dad4d){
}

void Stratum_use_f38e4ba456a0cc9a::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx\tv"},{"auxArity","0"},{"fact-dir","."},{"name","use"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 3, \"params\": [\"f\", \"x\", \"v\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"s:Statement\", \"s:Var\"]}}"}});
if (!inputDirectory.empty()) {directiveMap["fact-dir"] = inputDirectory;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_use_e955e932f22dad4d);
} catch (std::exception& e) {std::cerr << "Error loading use data: " << e.what() << '\n';
exit(1);
}
}
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Sf_stack_roots: public SouffleProgram {
public:
 Sf_stack_roots();
 ~Sf_stack_roots();
void run();
void runAll(std::string inputDirectoryArg = "",std::string outputDirectoryArg = "",bool performIOArg = true,bool pruneImdtRelsArg = true);
void printAll([[maybe_unused]] std::string outputDirectoryArg = "");
void loadAll([[maybe_unused]] std::string inputDirectoryArg = "");
void dumpInputs();
void dumpOutputs();
SymbolTable& getSymbolTable();
RecordTable& getRecordTable();
void setNumThreads(std::size_t numThreadsValue);
void executeSubroutine(std::string name,const std::vector<RamDomain>& args,std::vector<RamDomain>& ret);
private:
void runFunction(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg);
SymbolTableImpl symTable;
SpecializedRecordTable<0> recordTable;
ConcurrentCache<std::string,std::regex> regexCache;
Own<t_btree_000_iii__0_1_2__110__111::Type> rel_cf_edge_4931a04c8c74bb72;
souffle::RelationWrapper<t_btree_000_iii__0_1_2__110__111::Type> wrapper_rel_cf_edge_4931a04c8c74bb72;
Own<t_btree_000_ii__0_1__11__10::Type> rel_collect_092686b367d9983d;
souffle::RelationWrapper<t_btree_000_ii__0_1__11__10::Type> wrapper_rel_collect_092686b367d9983d;
Own<t_btree_000_iii__0_2_1__101__111::Type> rel_def_a2557aec54a7a800;
souffle::RelationWrapper<t_btree_000_iii__0_2_1__101__111::Type> wrapper_rel_def_a2557aec54a7a800;
Own<t_btree_000_iii__0_1_2__111::Type> rel_use_e955e932f22dad4d;
souffle::RelationWrapper<t_btree_000_iii__0_1_2__111::Type> wrapper_rel_use_e955e932f22dad4d;
Own<t_btree_000_iii__0_1_2__111::Type> rel_cf_path_018f9b04e61e101f;
souffle::RelationWrapper<t_btree_000_iii__0_1_2__111::Type> wrapper_rel_cf_path_018f9b04e61e101f;
Own<t_btree_000_iii__0_1_2__111::Type> rel_new_cf_path_7c1a0790df10e865;
Own<t_btree_000_iii__0_1_2__111::Type> rel_delta_cf_path_a939c29cb29cb918;
Own<t_btree_000_ii__0_1__11::Type> rel_root_vars_9dd5ee9984886e0d;
souffle::RelationWrapper<t_btree_000_ii__0_1__11::Type> wrapper_rel_root_vars_9dd5ee9984886e0d;
Stratum_cf_edge_c2ae152829fd6f1f stratum_cf_edge_4017fef287699967;
Stratum_cf_path_281344c75720c946 stratum_cf_path_2132d5848b095b9a;
Stratum_collect_77936cd6fddc6c8c stratum_collect_e5356b85e8033273;
Stratum_def_6f7db9860aa6b531 stratum_def_1d1da3266d2fd4ce;
Stratum_root_vars_d910841585fde373 stratum_root_vars_19aeb1b6f3a71208;
Stratum_use_f38e4ba456a0cc9a stratum_use_2e20cb5441769259;
std::string inputDirectory;
std::string outputDirectory;
SignalHandler* signalHandler{SignalHandler::instance()};
std::atomic<RamDomain> ctr{};
std::atomic<std::size_t> iter{};
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Sf_stack_roots::Sf_stack_roots():
symTable(),
recordTable(),
regexCache(),
rel_cf_edge_4931a04c8c74bb72(mk<t_btree_000_iii__0_1_2__110__111::Type>()),
wrapper_rel_cf_edge_4931a04c8c74bb72(0, *rel_cf_edge_4931a04c8c74bb72, *this, "cf_edge", std::array<const char *,3>{{"s:Function","s:Statement","s:Statement"}}, std::array<const char *,3>{{"f","x","y"}}, 0),
rel_collect_092686b367d9983d(mk<t_btree_000_ii__0_1__11__10::Type>()),
wrapper_rel_collect_092686b367d9983d(1, *rel_collect_092686b367d9983d, *this, "collect", std::array<const char *,2>{{"s:Function","s:Statement"}}, std::array<const char *,2>{{"f","x"}}, 0),
rel_def_a2557aec54a7a800(mk<t_btree_000_iii__0_2_1__101__111::Type>()),
wrapper_rel_def_a2557aec54a7a800(2, *rel_def_a2557aec54a7a800, *this, "def", std::array<const char *,3>{{"s:Function","s:Statement","s:Var"}}, std::array<const char *,3>{{"f","x","v"}}, 0),
rel_use_e955e932f22dad4d(mk<t_btree_000_iii__0_1_2__111::Type>()),
wrapper_rel_use_e955e932f22dad4d(3, *rel_use_e955e932f22dad4d, *this, "use", std::array<const char *,3>{{"s:Function","s:Statement","s:Var"}}, std::array<const char *,3>{{"f","x","v"}}, 0),
rel_cf_path_018f9b04e61e101f(mk<t_btree_000_iii__0_1_2__111::Type>()),
wrapper_rel_cf_path_018f9b04e61e101f(4, *rel_cf_path_018f9b04e61e101f, *this, "cf_path", std::array<const char *,3>{{"s:Function","s:Statement","s:Statement"}}, std::array<const char *,3>{{"f","x","y"}}, 0),
rel_new_cf_path_7c1a0790df10e865(mk<t_btree_000_iii__0_1_2__111::Type>()),
rel_delta_cf_path_a939c29cb29cb918(mk<t_btree_000_iii__0_1_2__111::Type>()),
rel_root_vars_9dd5ee9984886e0d(mk<t_btree_000_ii__0_1__11::Type>()),
wrapper_rel_root_vars_9dd5ee9984886e0d(5, *rel_root_vars_9dd5ee9984886e0d, *this, "root_vars", std::array<const char *,2>{{"s:Function","s:Var"}}, std::array<const char *,2>{{"f","v"}}, 0),
stratum_cf_edge_4017fef287699967(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_cf_edge_4931a04c8c74bb72),
stratum_cf_path_2132d5848b095b9a(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_delta_cf_path_a939c29cb29cb918,*rel_new_cf_path_7c1a0790df10e865,*rel_cf_edge_4931a04c8c74bb72,*rel_cf_path_018f9b04e61e101f),
stratum_collect_e5356b85e8033273(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_collect_092686b367d9983d),
stratum_def_1d1da3266d2fd4ce(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_def_a2557aec54a7a800),
stratum_root_vars_19aeb1b6f3a71208(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_cf_path_018f9b04e61e101f,*rel_collect_092686b367d9983d,*rel_def_a2557aec54a7a800,*rel_root_vars_9dd5ee9984886e0d,*rel_use_e955e932f22dad4d),
stratum_use_2e20cb5441769259(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_use_e955e932f22dad4d){
addRelation("cf_edge", wrapper_rel_cf_edge_4931a04c8c74bb72, true, false);
addRelation("collect", wrapper_rel_collect_092686b367d9983d, true, false);
addRelation("def", wrapper_rel_def_a2557aec54a7a800, true, false);
addRelation("use", wrapper_rel_use_e955e932f22dad4d, true, false);
addRelation("cf_path", wrapper_rel_cf_path_018f9b04e61e101f, false, false);
addRelation("root_vars", wrapper_rel_root_vars_9dd5ee9984886e0d, false, true);
}

 Sf_stack_roots::~Sf_stack_roots(){
}

void Sf_stack_roots::runFunction(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg){

    this->inputDirectory  = std::move(inputDirectoryArg);
    this->outputDirectory = std::move(outputDirectoryArg);
    this->performIO       = performIOArg;
    this->pruneImdtRels   = pruneImdtRelsArg;

    // set default threads (in embedded mode)
    // if this is not set, and omp is used, the default omp setting of number of cores is used.
#if defined(_OPENMP)
    if (0 < getNumThreads()) { omp_set_num_threads(static_cast<int>(getNumThreads())); }
#endif

    signalHandler->set();
// -- query evaluation --
{
 std::vector<RamDomain> args, ret;
stratum_cf_edge_4017fef287699967.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_collect_e5356b85e8033273.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_def_1d1da3266d2fd4ce.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_use_2e20cb5441769259.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_cf_path_2132d5848b095b9a.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_root_vars_19aeb1b6f3a71208.run(args, ret);
}

// -- relation hint statistics --
signalHandler->reset();
}

void Sf_stack_roots::run(){
runFunction("", "", false, false);
}

void Sf_stack_roots::runAll(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg){
runFunction(inputDirectoryArg, outputDirectoryArg, performIOArg, pruneImdtRelsArg);
}

void Sf_stack_roots::printAll([[maybe_unused]] std::string outputDirectoryArg){
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tv"},{"auxArity","0"},{"name","root_vars"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"v\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"s:Var\"]}}"}});
if (!outputDirectoryArg.empty()) {directiveMap["output-dir"] = outputDirectoryArg;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_root_vars_9dd5ee9984886e0d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

void Sf_stack_roots::loadAll([[maybe_unused]] std::string inputDirectoryArg){
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx\ty"},{"auxArity","0"},{"fact-dir","."},{"name","cf_edge"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 3, \"params\": [\"f\", \"x\", \"y\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"s:Statement\", \"s:Statement\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_cf_edge_4931a04c8c74bb72);
} catch (std::exception& e) {std::cerr << "Error loading cf_edge data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx"},{"auxArity","0"},{"fact-dir","."},{"name","collect"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 2, \"params\": [\"f\", \"x\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 2, \"types\": [\"s:Function\", \"s:Statement\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_collect_092686b367d9983d);
} catch (std::exception& e) {std::cerr << "Error loading collect data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx\tv"},{"auxArity","0"},{"fact-dir","."},{"name","def"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 3, \"params\": [\"f\", \"x\", \"v\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"s:Statement\", \"s:Var\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_def_a2557aec54a7a800);
} catch (std::exception& e) {std::cerr << "Error loading def data: " << e.what() << '\n';
exit(1);
}
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","f\tx\tv"},{"auxArity","0"},{"fact-dir","."},{"name","use"},{"operation","input"},{"params","{\"records\": {}, \"relation\": {\"arity\": 3, \"params\": [\"f\", \"x\", \"v\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 3, \"types\": [\"s:Function\", \"s:Statement\", \"s:Var\"]}}"}});
if (!inputDirectoryArg.empty()) {directiveMap["fact-dir"] = inputDirectoryArg;}
IOSystem::getInstance().getReader(directiveMap, symTable, recordTable)->readAll(*rel_use_e955e932f22dad4d);
} catch (std::exception& e) {std::cerr << "Error loading use data: " << e.what() << '\n';
exit(1);
}
}

void Sf_stack_roots::dumpInputs(){
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "cf_edge";
rwOperation["types"] = "{\"relation\": {\"arity\": 3, \"auxArity\": 0, \"types\": [\"s:Function\", \"s:Statement\", \"s:Statement\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_cf_edge_4931a04c8c74bb72);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "collect";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"s:Function\", \"s:Statement\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_collect_092686b367d9983d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "def";
rwOperation["types"] = "{\"relation\": {\"arity\": 3, \"auxArity\": 0, \"types\": [\"s:Function\", \"s:Statement\", \"s:Var\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_def_a2557aec54a7a800);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "use";
rwOperation["types"] = "{\"relation\": {\"arity\": 3, \"auxArity\": 0, \"types\": [\"s:Function\", \"s:Statement\", \"s:Var\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_use_e955e932f22dad4d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

void Sf_stack_roots::dumpOutputs(){
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "root_vars";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"s:Function\", \"s:Var\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_root_vars_9dd5ee9984886e0d);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

SymbolTable& Sf_stack_roots::getSymbolTable(){
return symTable;
}

RecordTable& Sf_stack_roots::getRecordTable(){
return recordTable;
}

void Sf_stack_roots::setNumThreads(std::size_t numThreadsValue){
SouffleProgram::setNumThreads(numThreadsValue);
symTable.setNumLanes(getNumThreads());
recordTable.setNumLanes(getNumThreads());
regexCache.setNumLanes(getNumThreads());
}

void Sf_stack_roots::executeSubroutine(std::string name,const std::vector<RamDomain>& args,std::vector<RamDomain>& ret){
if (name == "cf_edge") {
stratum_cf_edge_4017fef287699967.run(args, ret);
return;}
if (name == "cf_path") {
stratum_cf_path_2132d5848b095b9a.run(args, ret);
return;}
if (name == "collect") {
stratum_collect_e5356b85e8033273.run(args, ret);
return;}
if (name == "def") {
stratum_def_1d1da3266d2fd4ce.run(args, ret);
return;}
if (name == "root_vars") {
stratum_root_vars_19aeb1b6f3a71208.run(args, ret);
return;}
if (name == "use") {
stratum_use_2e20cb5441769259.run(args, ret);
return;}
fatal(("unknown subroutine " + name).c_str());
}

} // namespace  souffle
namespace souffle {
SouffleProgram *newInstance_stack_roots(){return new  souffle::Sf_stack_roots;}
SymbolTable *getST_stack_roots(SouffleProgram *p){return &reinterpret_cast<souffle::Sf_stack_roots*>(p)->getSymbolTable();}
} // namespace souffle

#ifndef __EMBEDDED_SOUFFLE__
#include "souffle/CompiledOptions.h"
int main(int argc, char** argv)
{
try{
souffle::CmdOptions opt(R"(mycpp/stack_roots.dl)",
R"()",
R"()",
false,
R"()",
1);
if (!opt.parse(argc,argv)) return 1;
souffle::Sf_stack_roots obj;
#if defined(_OPENMP) 
obj.setNumThreads(opt.getNumJobs());

#endif
obj.runAll(opt.getInputFileDir(), opt.getOutputFileDir());
return 0;
} catch(std::exception &e) { souffle::SignalHandler::instance()->error(e.what());}
}
#endif

namespace  souffle {
using namespace souffle;
class factory_Sf_stack_roots: souffle::ProgramFactory {
public:
souffle::SouffleProgram* newInstance();
 factory_Sf_stack_roots();
private:
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
souffle::SouffleProgram* factory_Sf_stack_roots::newInstance(){
return new  souffle::Sf_stack_roots();
}

 factory_Sf_stack_roots::factory_Sf_stack_roots():
souffle::ProgramFactory("stack_roots"){
}

} // namespace  souffle
namespace souffle {

#ifdef __EMBEDDED_SOUFFLE__
extern "C" {
souffle::factory_Sf_stack_roots __factory_Sf_stack_roots_instance;
}
#endif
} // namespace souffle


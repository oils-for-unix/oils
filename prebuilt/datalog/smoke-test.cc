#define SOUFFLE_GENERATOR_VERSION "39d42a366"
#include "souffle/CompiledSouffle.h"
#include "souffle/SignalHandler.h"
#include "souffle/SouffleInterface.h"
#include "souffle/datastructure/BTree.h"
#include "souffle/io/IOSystem.h"
#include <any>
namespace functors {
extern "C" {
}
} //namespace functors
namespace souffle::t_btree_ii__0_1__11 {
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
} // namespace souffle::t_btree_ii__0_1__11 
namespace souffle::t_btree_ii__0_1__11 {
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
} // namespace souffle::t_btree_ii__0_1__11 
namespace souffle::t_btree_ii__0_1__11__10 {
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
} // namespace souffle::t_btree_ii__0_1__11__10 
namespace souffle::t_btree_ii__0_1__11__10 {
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
} // namespace souffle::t_btree_ii__0_1__11__10 
namespace  souffle {
using namespace souffle;
class Stratum_edge_9543a759b165a2cb {
public:
 Stratum_edge_9543a759b165a2cb(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_ii__0_1__11::Type& rel_edge_04d25f5060e9043b);
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
t_btree_ii__0_1__11::Type* rel_edge_04d25f5060e9043b;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_edge_9543a759b165a2cb::Stratum_edge_9543a759b165a2cb(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_ii__0_1__11::Type& rel_edge_04d25f5060e9043b):
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
rel_edge_04d25f5060e9043b(&rel_edge_04d25f5060e9043b){
}

void Stratum_edge_9543a759b165a2cb::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(edge(1,2).
in file smoke-test.dl [3:1-3:12])_");
[&](){
CREATE_OP_CONTEXT(rel_edge_04d25f5060e9043b_op_ctxt,rel_edge_04d25f5060e9043b->createContext());
Tuple<RamDomain,2> tuple{{ramBitCast(RamSigned(1)),ramBitCast(RamSigned(2))}};
rel_edge_04d25f5060e9043b->insert(tuple,READ_OP_CONTEXT(rel_edge_04d25f5060e9043b_op_ctxt));
}
();signalHandler->setMsg(R"_(edge(2,3).
in file smoke-test.dl [4:1-4:12])_");
[&](){
CREATE_OP_CONTEXT(rel_edge_04d25f5060e9043b_op_ctxt,rel_edge_04d25f5060e9043b->createContext());
Tuple<RamDomain,2> tuple{{ramBitCast(RamSigned(2)),ramBitCast(RamSigned(3))}};
rel_edge_04d25f5060e9043b->insert(tuple,READ_OP_CONTEXT(rel_edge_04d25f5060e9043b_op_ctxt));
}
();}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Stratum_path_614f1ce382100c3f {
public:
 Stratum_path_614f1ce382100c3f(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_ii__0_1__11__10::Type& rel_delta_path_23da6daa27e8b245,t_btree_ii__0_1__11__10::Type& rel_new_path_a0453b38c2806942,t_btree_ii__0_1__11::Type& rel_edge_04d25f5060e9043b,t_btree_ii__0_1__11::Type& rel_path_76cf4ab0e06a645b);
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
t_btree_ii__0_1__11__10::Type* rel_delta_path_23da6daa27e8b245;
t_btree_ii__0_1__11__10::Type* rel_new_path_a0453b38c2806942;
t_btree_ii__0_1__11::Type* rel_edge_04d25f5060e9043b;
t_btree_ii__0_1__11::Type* rel_path_76cf4ab0e06a645b;
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Stratum_path_614f1ce382100c3f::Stratum_path_614f1ce382100c3f(SymbolTable& symTable,RecordTable& recordTable,ConcurrentCache<std::string,std::regex>& regexCache,bool& pruneImdtRels,bool& performIO,SignalHandler*& signalHandler,std::atomic<std::size_t>& iter,std::atomic<RamDomain>& ctr,std::string& inputDirectory,std::string& outputDirectory,t_btree_ii__0_1__11__10::Type& rel_delta_path_23da6daa27e8b245,t_btree_ii__0_1__11__10::Type& rel_new_path_a0453b38c2806942,t_btree_ii__0_1__11::Type& rel_edge_04d25f5060e9043b,t_btree_ii__0_1__11::Type& rel_path_76cf4ab0e06a645b):
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
rel_delta_path_23da6daa27e8b245(&rel_delta_path_23da6daa27e8b245),
rel_new_path_a0453b38c2806942(&rel_new_path_a0453b38c2806942),
rel_edge_04d25f5060e9043b(&rel_edge_04d25f5060e9043b),
rel_path_76cf4ab0e06a645b(&rel_path_76cf4ab0e06a645b){
}

void Stratum_path_614f1ce382100c3f::run([[maybe_unused]] const std::vector<RamDomain>& args,[[maybe_unused]] std::vector<RamDomain>& ret){
signalHandler->setMsg(R"_(path(u,v) :- 
   edge(u,v).
in file smoke-test.dl [9:1-9:26])_");
if(!(rel_edge_04d25f5060e9043b->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_edge_04d25f5060e9043b_op_ctxt,rel_edge_04d25f5060e9043b->createContext());
CREATE_OP_CONTEXT(rel_path_76cf4ab0e06a645b_op_ctxt,rel_path_76cf4ab0e06a645b->createContext());
for(const auto& env0 : *rel_edge_04d25f5060e9043b) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1])}};
rel_path_76cf4ab0e06a645b->insert(tuple,READ_OP_CONTEXT(rel_path_76cf4ab0e06a645b_op_ctxt));
}
}
();}
[&](){
CREATE_OP_CONTEXT(rel_delta_path_23da6daa27e8b245_op_ctxt,rel_delta_path_23da6daa27e8b245->createContext());
CREATE_OP_CONTEXT(rel_path_76cf4ab0e06a645b_op_ctxt,rel_path_76cf4ab0e06a645b->createContext());
for(const auto& env0 : *rel_path_76cf4ab0e06a645b) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1])}};
rel_delta_path_23da6daa27e8b245->insert(tuple,READ_OP_CONTEXT(rel_delta_path_23da6daa27e8b245_op_ctxt));
}
}
();auto loop_counter = RamUnsigned(1);
iter = 0;
for(;;) {
signalHandler->setMsg(R"_(path(u,w) :- 
   edge(u,v),
   path(v,w).
in file smoke-test.dl [10:1-10:38])_");
if(!(rel_edge_04d25f5060e9043b->empty()) && !(rel_delta_path_23da6daa27e8b245->empty())) {
[&](){
CREATE_OP_CONTEXT(rel_delta_path_23da6daa27e8b245_op_ctxt,rel_delta_path_23da6daa27e8b245->createContext());
CREATE_OP_CONTEXT(rel_new_path_a0453b38c2806942_op_ctxt,rel_new_path_a0453b38c2806942->createContext());
CREATE_OP_CONTEXT(rel_edge_04d25f5060e9043b_op_ctxt,rel_edge_04d25f5060e9043b->createContext());
CREATE_OP_CONTEXT(rel_path_76cf4ab0e06a645b_op_ctxt,rel_path_76cf4ab0e06a645b->createContext());
for(const auto& env0 : *rel_edge_04d25f5060e9043b) {
auto range = rel_delta_path_23da6daa27e8b245->lowerUpperRange_10(Tuple<RamDomain,2>{{ramBitCast(env0[1]), ramBitCast<RamDomain>(MIN_RAM_SIGNED)}},Tuple<RamDomain,2>{{ramBitCast(env0[1]), ramBitCast<RamDomain>(MAX_RAM_SIGNED)}},READ_OP_CONTEXT(rel_delta_path_23da6daa27e8b245_op_ctxt));
for(const auto& env1 : range) {
if( !(rel_path_76cf4ab0e06a645b->contains(Tuple<RamDomain,2>{{ramBitCast(env0[0]),ramBitCast(env1[1])}},READ_OP_CONTEXT(rel_path_76cf4ab0e06a645b_op_ctxt)))) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env1[1])}};
rel_new_path_a0453b38c2806942->insert(tuple,READ_OP_CONTEXT(rel_new_path_a0453b38c2806942_op_ctxt));
}
}
}
}
();}
if(rel_new_path_a0453b38c2806942->empty()) break;
[&](){
CREATE_OP_CONTEXT(rel_new_path_a0453b38c2806942_op_ctxt,rel_new_path_a0453b38c2806942->createContext());
CREATE_OP_CONTEXT(rel_path_76cf4ab0e06a645b_op_ctxt,rel_path_76cf4ab0e06a645b->createContext());
for(const auto& env0 : *rel_new_path_a0453b38c2806942) {
Tuple<RamDomain,2> tuple{{ramBitCast(env0[0]),ramBitCast(env0[1])}};
rel_path_76cf4ab0e06a645b->insert(tuple,READ_OP_CONTEXT(rel_path_76cf4ab0e06a645b_op_ctxt));
}
}
();std::swap(rel_delta_path_23da6daa27e8b245, rel_new_path_a0453b38c2806942);
rel_new_path_a0453b38c2806942->purge();
loop_counter = (ramBitCast<RamUnsigned>(loop_counter) + ramBitCast<RamUnsigned>(RamUnsigned(1)));
iter++;
}
iter = 0;
rel_delta_path_23da6daa27e8b245->purge();
rel_new_path_a0453b38c2806942->purge();
if (performIO) {
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","u\tv"},{"auxArity","0"},{"filename","path.tsv"},{"name","path"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {}, \"relation\": {\"arity\": 2, \"params\": [\"u\", \"v\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 2, \"types\": [\"i:number\", \"i:number\"]}}"}});
if (outputDirectory == "-"){directiveMap["IO"] = "stdout"; directiveMap["headers"] = "true";}
else if (!outputDirectory.empty()) {directiveMap["output-dir"] = outputDirectory;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_path_76cf4ab0e06a645b);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}
if (pruneImdtRels) rel_edge_04d25f5060e9043b->purge();
}

} // namespace  souffle

namespace  souffle {
using namespace souffle;
class Sf__: public SouffleProgram {
public:
 Sf__();
 ~Sf__();
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
Own<t_btree_ii__0_1__11::Type> rel_edge_04d25f5060e9043b;
souffle::RelationWrapper<t_btree_ii__0_1__11::Type> wrapper_rel_edge_04d25f5060e9043b;
Own<t_btree_ii__0_1__11::Type> rel_path_76cf4ab0e06a645b;
souffle::RelationWrapper<t_btree_ii__0_1__11::Type> wrapper_rel_path_76cf4ab0e06a645b;
Own<t_btree_ii__0_1__11__10::Type> rel_delta_path_23da6daa27e8b245;
Own<t_btree_ii__0_1__11__10::Type> rel_new_path_a0453b38c2806942;
Stratum_edge_9543a759b165a2cb stratum_edge_31e40d0d94fe9f7c;
Stratum_path_614f1ce382100c3f stratum_path_2eecd83fe9440b5c;
std::string inputDirectory;
std::string outputDirectory;
SignalHandler* signalHandler{SignalHandler::instance()};
std::atomic<RamDomain> ctr{};
std::atomic<std::size_t> iter{};
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
 Sf__::Sf__():
symTable(),
recordTable(),
regexCache(),
rel_edge_04d25f5060e9043b(mk<t_btree_ii__0_1__11::Type>()),
wrapper_rel_edge_04d25f5060e9043b(0, *rel_edge_04d25f5060e9043b, *this, "edge", std::array<const char *,2>{{"i:number","i:number"}}, std::array<const char *,2>{{"u","v"}}, 0),
rel_path_76cf4ab0e06a645b(mk<t_btree_ii__0_1__11::Type>()),
wrapper_rel_path_76cf4ab0e06a645b(1, *rel_path_76cf4ab0e06a645b, *this, "path", std::array<const char *,2>{{"i:number","i:number"}}, std::array<const char *,2>{{"u","v"}}, 0),
rel_delta_path_23da6daa27e8b245(mk<t_btree_ii__0_1__11__10::Type>()),
rel_new_path_a0453b38c2806942(mk<t_btree_ii__0_1__11__10::Type>()),
stratum_edge_31e40d0d94fe9f7c(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_edge_04d25f5060e9043b),
stratum_path_2eecd83fe9440b5c(symTable,recordTable,regexCache,pruneImdtRels,performIO,signalHandler,iter,ctr,inputDirectory,outputDirectory,*rel_delta_path_23da6daa27e8b245,*rel_new_path_a0453b38c2806942,*rel_edge_04d25f5060e9043b,*rel_path_76cf4ab0e06a645b){
addRelation("edge", wrapper_rel_edge_04d25f5060e9043b, false, false);
addRelation("path", wrapper_rel_path_76cf4ab0e06a645b, false, true);
}

 Sf__::~Sf__(){
}

void Sf__::runFunction(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg){

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
stratum_edge_31e40d0d94fe9f7c.run(args, ret);
}
{
 std::vector<RamDomain> args, ret;
stratum_path_2eecd83fe9440b5c.run(args, ret);
}

// -- relation hint statistics --
signalHandler->reset();
}

void Sf__::run(){
runFunction("", "", false, false);
}

void Sf__::runAll(std::string inputDirectoryArg,std::string outputDirectoryArg,bool performIOArg,bool pruneImdtRelsArg){
runFunction(inputDirectoryArg, outputDirectoryArg, performIOArg, pruneImdtRelsArg);
}

void Sf__::printAll([[maybe_unused]] std::string outputDirectoryArg){
try {std::map<std::string, std::string> directiveMap({{"IO","file"},{"attributeNames","u\tv"},{"auxArity","0"},{"filename","path.tsv"},{"name","path"},{"operation","output"},{"output-dir","."},{"params","{\"records\": {}, \"relation\": {\"arity\": 2, \"params\": [\"u\", \"v\"]}}"},{"types","{\"ADTs\": {}, \"records\": {}, \"relation\": {\"arity\": 2, \"types\": [\"i:number\", \"i:number\"]}}"}});
if (!outputDirectoryArg.empty()) {directiveMap["output-dir"] = outputDirectoryArg;}
IOSystem::getInstance().getWriter(directiveMap, symTable, recordTable)->writeAll(*rel_path_76cf4ab0e06a645b);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

void Sf__::loadAll([[maybe_unused]] std::string inputDirectoryArg){
}

void Sf__::dumpInputs(){
}

void Sf__::dumpOutputs(){
try {std::map<std::string, std::string> rwOperation;
rwOperation["IO"] = "stdout";
rwOperation["name"] = "path";
rwOperation["types"] = "{\"relation\": {\"arity\": 2, \"auxArity\": 0, \"types\": [\"i:number\", \"i:number\"]}}";
IOSystem::getInstance().getWriter(rwOperation, symTable, recordTable)->writeAll(*rel_path_76cf4ab0e06a645b);
} catch (std::exception& e) {std::cerr << e.what();exit(1);}
}

SymbolTable& Sf__::getSymbolTable(){
return symTable;
}

RecordTable& Sf__::getRecordTable(){
return recordTable;
}

void Sf__::setNumThreads(std::size_t numThreadsValue){
SouffleProgram::setNumThreads(numThreadsValue);
symTable.setNumLanes(getNumThreads());
recordTable.setNumLanes(getNumThreads());
regexCache.setNumLanes(getNumThreads());
}

void Sf__::executeSubroutine(std::string name,const std::vector<RamDomain>& args,std::vector<RamDomain>& ret){
if (name == "edge") {
stratum_edge_31e40d0d94fe9f7c.run(args, ret);
return;}
if (name == "path") {
stratum_path_2eecd83fe9440b5c.run(args, ret);
return;}
fatal(("unknown subroutine " + name).c_str());
}

} // namespace  souffle
namespace souffle {
SouffleProgram *newInstance__(){return new  souffle::Sf__;}
SymbolTable *getST__(SouffleProgram *p){return &reinterpret_cast<souffle::Sf__*>(p)->getSymbolTable();}
} // namespace souffle

#ifndef __EMBEDDED_SOUFFLE__
#include "souffle/CompiledOptions.h"
int main(int argc, char** argv)
{
try{
souffle::CmdOptions opt(R"(deps/source.medo/souffle/smoke-test.dl)",
R"()",
R"()",
false,
R"()",
1);
if (!opt.parse(argc,argv)) return 1;
souffle::Sf__ obj;
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
class factory_Sf__: souffle::ProgramFactory {
public:
souffle::SouffleProgram* newInstance();
 factory_Sf__();
private:
};
} // namespace  souffle
namespace  souffle {
using namespace souffle;
souffle::SouffleProgram* factory_Sf__::newInstance(){
return new  souffle::Sf__();
}

 factory_Sf__::factory_Sf__():
souffle::ProgramFactory("_"){
}

} // namespace  souffle
namespace souffle {

#ifdef __EMBEDDED_SOUFFLE__
extern "C" {
souffle::factory_Sf__ __factory_Sf___instance;
}
#endif
} // namespace souffle


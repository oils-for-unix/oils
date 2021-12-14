CFLAGS := -Wall -g

OBJS := parser.o \
	tokenizer.o \
	grammar1.o \
	grammar.o \
        bitset.o \
        node.o \
	python.o \
	acceler.o \
        listnode.o \
	python_grammar.o \
	parsetok.o \
	main.o

run: all
	./test

all: clean test

.PHONY: parser
test: $(OBJS)
	gcc -o test $^ $(CFLAGS) $(LDFLAGS)

.PHONY: clean
clean:
	rm -rf *.o
	rm -f test

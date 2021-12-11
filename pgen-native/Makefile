CFLAGS := -Wall

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

parser: $(OBJS)
	gcc -o parser $^ $(CFLAGS) $(LDFLAGS)

all: clean parser

.PHONY: clean
clean:
	rm -rf *.o
	rm parser

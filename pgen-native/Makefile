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
	main.o

parser: $(OBJS)
	gcc -o parser $^ $(CFLAGS) $(LDFLAGS)

all: clean parser

.PHONY: clean
clean:
	rm -rf *.o

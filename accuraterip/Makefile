CFLAGS+=-Wall -Wextra -Werror
CFLAGS+=--std=c99
CFLAGS+=-O3
#CFLAGS+=-ggdb3
#CFLAGS+=-fstack-check


OBJS=accuraterip.o cmdline.o
LIBS+=-lsndfile

.PHONY: all
all: accuraterip

.PHONY: clean
clean:
	-rm -f $(OBJS) accuraterip

accuraterip.c: accuraterip.h

accuraterip: $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LIBS)


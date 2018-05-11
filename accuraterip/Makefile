CFLAGS+=-Wall -Wextra -Werror
CFLAGS+=--std=c99
CFLAGS+=-O3
CFLAGS+=-ggdb3
CFLAGS+=-fstack-check


OBJS=accuraterip.o cmdline.o
LIBS+=-lsndfile

.PHONY: all
all: accuraterip test_short.wav

.PHONY: clean
clean:
	-rm -f $(OBJS) accuraterip
	-rm -f test_short.wav

accuraterip.c: accuraterip.h

accuraterip: $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LIBS)

test_short.wav: test.wav
	sox $< $@ trim 100 10

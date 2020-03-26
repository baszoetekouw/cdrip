CFLAGS+=-Wall -Wextra -Werror
CFLAGS+=--std=c99
CFLAGS+=-O3
CFLAGS+=-ggdb3
CFLAGS+=-fstack-check
CFLAGS+=-march=native


OBJS=accuraterip.o cmdline.o
LIBS+=-lsndfile

.PHONY: all
all: short.wav

.PHONY: test
test: short.wav

.PHONY: clean
clean:
	-rm -f short.wav full.wav

full.flac: JOHN_MICHEL_CELLO-J_S_BACH_CELLO_SUITE_1_in_G_Minuets.ogg
	flac -9 $< $@

full.wav: full.flac
	flac -d -f  -o $@ $<

short.wav: full.wav
	sox $< $@ trim 30 10

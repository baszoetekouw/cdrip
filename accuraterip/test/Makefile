CFLAGS+=-Wall -Wextra -Werror
CFLAGS+=--std=c99
CFLAGS+=-O3
CFLAGS+=-ggdb3
CFLAGS+=-fstack-check
CFLAGS+=-march=native


OBJS=accuraterip.o cmdline.o
LIBS+=-lsndfile

.PHONY: all
all: full.wav short.wav short2.wav short3.wav shifted.wav

.PHONY: test
test: short.wav

.PHONY: clean
clean:
	-rm -f short.wav short2.wav short3.wav full.wav

full.flac: JOHN_MICHEL_CELLO-J_S_BACH_CELLO_SUITE_1_in_G_Minuets.ogg
	flac -9 $< $@

full.wav: full.flac
	flac -d -f  -o $@ $<

short.wav: full.wav
	sox $< $@ trim 30 20

short2.wav: full.wav
	sox $< $@ trim 50 25

short3.wav: full.wav
	sox $< $@ trim 75 30

# shift by 48 samples (==192 bytes)
shifted.wav: full.wav
	(ffmpeg -i $< -codec:a copy  -f s16le - | dd ibs=4 skip=48; dd if=/dev/zero ibs=4 count=48 conv=notrunc oflag=append) | ffmpeg -f s16le -ac 2 -i - -y $@


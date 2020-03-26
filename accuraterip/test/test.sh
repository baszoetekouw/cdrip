#!/bin/bash

# original checksum calculated using https://github.com/leo-bogert/accuraterip-checksum

# note that checksum for middle and last track are identical; this is because the sound file ends with >5s of silence
# this is exactly why this checksum sucks
FULL_V2_NORMAL=bfb443d3
FULL_V2_FIRST=673123e9
FULL_V2_LAST=bfb443d3

FULL_V1_NORMAL=e098daf7
FULL_V1_FIRST=881b8b37
FULL_V1_LAST=e098daf7

SHORT_V2_NORMAL=0360d7e7
SHORT_V2_FIRST=d2ef1475
SHORT_V2_LAST=ed0fe3ce

SHORT_V1_NORMAL=d51656cE
SHORT_V1_FIRST=a4c44438
SHORT_V1_LAST=e2d97188


# check full file
chksums=($(../accuraterip full.wav))
echo -n "Test for full.wav (middle track)... "
if ! [ ${chksums[0]}=$FULL_V1_NORMAL -a ${chksums[1]}=$FULL_V1_NORMAL ]
then
	echo "FAILED"
	echo " - v1: expected $FULL_V1_NORMAL, got ${chksums[0]}"
	echo " - v2: expected $FULL_V2_NORMAL, got ${chksums[1]}"
else
	echo "OK"
fi

chksums=($(../accuraterip -f full.wav))
echo -n "Test for full.wav (first track)... "
if ! [ ${chksums[0]}=$FULL_V1_FIRST -a ${chksums[1]}=$FULL_V1_FIRST ]
then
	echo "FAILED"
	echo " - v1: expected $FULL_V1_FIRST, got ${chksums[0]}"
	echo " - v2: expected $FULL_V2_FIRST, got ${chksums[1]}"
else
	echo "OK"
fi

chksums=($(../accuraterip -l full.wav))
echo -n "Test for full.wav (last track)... "
if ! [ ${chksums[0]}=$FULL_V1_LAST -a ${chksums[1]}=$FULL_V1_LAST ]
then
	echo "FAILED"
	echo " - v1: expected $FULL_V1_LAST, got ${chksums[0]}"
	echo " - v2: expected $FULL_V2_LAST, got ${chksums[1]}"
else
	echo "OK"
fi


# check short file
chksums=($(../accuraterip short.wav))
echo -n "Test for short.wav (middle track)... "
if ! [ ${chksums[0]}=$SHORT_V1_NORMAL -a ${chksums[1]}=$SHORT_V1_NORMAL ]
then
	echo "FAILED"
	echo " - v1: expected $SHORT_V1_NORMAL, got ${chksums[0]}"
	echo " - v2: expected $SHORT_V2_NORMAL, got ${chksums[1]}"
else
	echo "OK"
fi

chksums=($(../accuraterip -f short.wav))
echo -n "Test for short.wav (first track)... "
if ! [ ${chksums[0]}=$SHORT_V1_FIRST -a ${chksums[1]}=$SHORT_V1_FIRST ]
then
	echo "FAILED"
	echo " - v1: expected $SHORT_V1_FIRST, got ${chksums[0]}"
	echo " - v2: expected $SHORT_V2_FIRST, got ${chksums[1]}"
else
	echo "OK"
fi

chksums=($(../accuraterip -l short.wav))
echo -n "Test for short.wav (last track)... "
if ! [ ${chksums[0]}=$SHORT_V1_LAST -a ${chksums[1]}=$SHORT_V1_LAST ]
then
	echo "FAILED"
	echo " - v1: expected $SHORT_V1_LAST, got ${chksums[0]}"
	echo " - v2: expected $SHORT_V2_LAST, got ${chksums[1]}"
else
	echo "OK"
fi

echo "Finished"

#!/bin/bash

# original checksum calculated using https://github.com/leo-bogert/accuraterip-checksum

# note that checksum for middle and last track are identical; this is because the sound file ends with >5s of silence
# this is exactly why this checksum sucks
FULL_V2_NORMAL=bfb443d3
FULL_V2_FIRST=673123e9
FULL_V2_LAST=bfb443d3
FULL_V2_SINGLE=673123e9

FULL_V1_NORMAL=e098daf7
FULL_V1_FIRST=881b8b37
FULL_V1_LAST=e098daf7
FULL_V1_SINGLE=881b8b37

SHORT_V2_NORMAL=2c5fda79
SHORT_V2_FIRST=fbee1707
SHORT_V2_LAST=2a4a6ee3
SHORT_V2_SINGLE=f9d8ab71

SHORT_V1_NORMAL=f45b5064
SHORT_V1_FIRST=c4093dce
SHORT_V1_LAST=3feb027c
SHORT_V1_SINGLE=0f98efe6

SHORT2_V2_NORMAL=32399085
SHORT2_V1_NORMAL=96dbf310

SHORT3_V2_LAST=38c4e03c
SHORT3_V1_LAST=ab7b4804

SHIFTED_V2_NORMAL=671a7f47
SHIFTED_V1_NORMAL=9496fdd7


function comp() {
	MSG=$1
	OK1=$2
	OK2=$3
	CHK1=$4
	CHK2=$5

	echo -n "Test for ${MSG}... "
	if ! [ "$OK1" = "$CHK1" -a "$OK2" = "$CHK2" ]
	then
		echo "FAILED"
		echo " - v1: expected $OK1, got $CHK1"
		echo " - v2: expected $OK2, got $CHK2"
	else
		echo "OK"
	fi
}


# check wav files
sha256sum --check <<EOF
e5f2b25ae2761e36505aff0c467106868a17ed1e856a9c1f26b0726e936bb3e2  full.wav
f5b265107db66510d89b6a18c04f55dec0dfbee0f7f729a6634c0cab3e51979e  shifted.wav
20d0d5e7de68e998eb336f190ed4891b20c114c37a289611119b14794d28c3b6  short2.wav
5db94a4738eaf64370f38818472150762760c2e4f5336aec7096f67c19e11804  short3.wav
0e47251cc80f9eab0756afc4f7c6736b7046b8b9f974cb88d0848c1d0c6a7fa1  short.wav
150331e03842a8362ae6656f3e543d4ff58899181d357a549be74c9d0646be87  test1.wav
c6c3bc34db4462079ea9a9f7734ad70ea0f328a36e7e7942734081c67acfb33f  test2.wav
EOF


# check full file
chksums=($(../accuraterip full.wav | awk '{print $4, $5}'))
comp "full.wav (middle track)... " $FULL_V1_NORMAL $FULL_V2_NORMAL ${chksums[@]}

chksums=($(../accuraterip -f full.wav | awk '{print $4, $5}'))
comp "full.wav (first track)... " $FULL_V1_FIRST $FULL_V2_FIRST ${chksums[@]}

chksums=($(../accuraterip -l full.wav | awk '{print $4, $5}'))
comp "full.wav (last track)... " $FULL_V1_LAST $FULL_V2_LAST ${chksums[@]}

chksums=($(../accuraterip -f -l full.wav | awk '{print $4, $5}'))
comp "full.wav (single track)... " $FULL_V1_SINGLE $FULL_V2_SINGLE ${chksums[@]}


# check short file
chksums=($(../accuraterip short.wav | awk '{print $4, $5}'))
comp "short.wav (middle track)... " $SHORT_V1_NORMAL $SHORT_V2_NORMAL ${chksums[@]}

chksums=($(../accuraterip -f short.wav | awk '{print $4, $5}'))
comp "short.wav (first track)... " $SHORT_V1_FIRST $SHORT_V2_FIRST ${chksums[@]}

chksums=($(../accuraterip -l short.wav | awk '{print $4, $5}'))
comp "short.wav (last track)... " $SHORT_V1_LAST $SHORT_V2_LAST ${chksums[@]}

chksums=($(../accuraterip -f -l short.wav | awk '{print $4, $5}'))
comp "short.wav (single track)... " $SHORT_V1_SINGLE $SHORT_V2_SINGLE ${chksums[@]}


# check long file subset
chksums=($(../accuraterip full.wav 30,20 | awk '{print $4, $5}'))
comp "subset of full.wav (middle track)... " $SHORT_V1_NORMAL $SHORT_V2_NORMAL ${chksums[@]}

chksums=($(../accuraterip -f full.wav 30,20 | awk '{print $4, $5}'))
comp "subset of full.wav (first track)... " $SHORT_V1_FIRST $SHORT_V2_FIRST ${chksums[@]}

chksums=($(../accuraterip -l full.wav 30,20 | awk '{print $4, $5}'))
comp "subset of full.wav (last track)... " $SHORT_V1_LAST $SHORT_V2_LAST ${chksums[@]}

chksums=($(../accuraterip -f -l full.wav 30,20 | awk '{print $4, $5}'))
comp "subset of full.wav (single track)... " $SHORT_V1_SINGLE $SHORT_V2_SINGLE ${chksums[@]}

# check long file multiple tracks
chksums=($(../accuraterip full.wav 30,20 50,25 75,30 | awk '{print $4, $5}'))
comp "subset of full.wav (track 1)... " $SHORT_V1_FIRST   $SHORT_V2_FIRST   ${chksums[@]:0:2}
comp "subset of full.wav (track 2)... " $SHORT2_V1_NORMAL $SHORT2_V2_NORMAL ${chksums[@]:2:2}
comp "subset of full.wav (track 3)... " $SHORT3_V1_LAST   $SHORT3_V2_LAST   ${chksums[@]:4:2}


# check offset handling
chksums=($(../accuraterip -o0 full.wav | awk '{print $4, $5}'))
comp "full.wav (middle track, shifted by 0)... " $FULL_V1_NORMAL $FULL_V2_NORMAL ${chksums[@]}

chksums=($(../accuraterip -o0 shifted.wav | awk '{print $4, $5}'))
comp "shifted.wav (middle track, shifted by 0)... " $SHIFTED_V1_NORMAL $SHIFTED_V2_NORMAL ${chksums[@]}

chksums=($(../accuraterip -o48 shifted.wav | awk '{print $4, $5}'))
comp "shifted.wav (middle track, shifted by 48)... " $FULL_V1_NORMAL $FULL_V2_NORMAL ${chksums[@]}



echo "Finished"

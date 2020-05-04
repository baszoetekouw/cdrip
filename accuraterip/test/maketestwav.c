#include <sndfile.h>
#include <stdio.h>

int main(void)
{
	SNDFILE *outfile;
	SF_INFO sfinfo;

	sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
	sfinfo.channels = 2;
	sfinfo.samplerate = 44100;

	if(!sf_format_check(&sfinfo))
	{
		printf("Invalid encoding\n");
		return 1;
	}

	if(!(outfile = sf_open("test1.wav", SFM_WRITE, &sfinfo)))
	{
		printf("Error : could not open file : %s\n", "test.wav");
		puts(sf_strerror(NULL));
		return 1;
	}

	for (short s=0; s<48; s++)
	{
		short buf[2] = {0,0};
		sf_write_short(outfile, buf, 2);
	}
	for (short s=0; s<128; s++)
	{
		short buf[2] = {s,s};
		sf_write_short(outfile, buf, 2);
	}

	sf_close(outfile);


	if(!(outfile = sf_open("test2.wav", SFM_WRITE, &sfinfo)))
	{
		printf("Error : could not open file : %s\n", "test.wav");
		puts(sf_strerror(NULL));
		return 1;
	}

	for (short s=0; s<128; s++)
	{
		short buf[2] = {s,s};
		sf_write_short(outfile, buf, 2);
	}
	for (short s=0; s<48; s++)
	{
		short buf[2] = {0,0};
		sf_write_short(outfile, buf, 2);
	}

	sf_close(outfile);

	printf("ok\n");

	return 0;
}


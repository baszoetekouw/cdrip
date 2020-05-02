#include "accuraterip.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>

samplenum_t parse_time(const char * const time_str, const size_t buf_size)
{
    /* We're going to parse a time input string
     * These strings can be either in the form "<samples>s" to specify a fixed number of samples
     * right away, or in the form "[[<min>:]<sec>:]<frames>" to specify minutes, seconds, and frames.
     * Note: 4 bytes (16 bits x 2 channels) in a sample, 588 samples in a frame, 75 frames in a second
     */

    /* copy the string to a local buffer, to make sure it's NULL-terminated */
    char buff[buf_size + 1];
    memset(buff, 0, sizeof(buff));
    strncpy(buff, time_str, buf_size);
    buff[buf_size] = '\0';

    /* pointer to current position in buffer */
    char *p1, *p2, *p3;

    /* fetch first number in the string */
    long num1 = strtol(buff,&p1,10);
    if (num1<0)
    {
        /* invalid (negative) number was specified */
        help("Invalid time specification (negative number)");
    }
    if (p1==buff)
    {
        /* pointer hasn't moved, so there was no number to decode */
        help("Invalid time specified");
    }

    /* if the next char is an 's' (or 'S'), assume first number is a number of samples */
    if (*p1=='s' || *p1=='S')
    {
        return num1;
    }

    /* fetch second number in the string */
    long num2 = strtol(++p1,&p2,10);
    if (num2<0)
    {
        /* invalid (negative) number was specified */
        help("Invalid time specification (negative number)");
    }
    if (p2==p1)
    {
        /* pointer hasn't moved, so there was no number to decode,
         * which means num1 is the final answer, and should be interpreted as a number of SECONDS */
        return num1*SAMPLES_PER_SECOND;
    }

    /* fetch third number in the string */
    long num3 = strtol(++p2,&p3,10);
    if (num3<0)
    {
        /* invalid (negative) number was specified */
        help("Invalid time specification (negative number)");
    }
    if (p3==p2)
    {
        /* pointer hasn't moved, so there was no number to decode,
         * which means num1:num2 is the final answer, and should be interpretated as seconds:frames */
        return num1*SAMPLES_PER_SECOND + num2*SAMPLES_PER_FRAME;
    }

    /* otherwise, we got minutes:seconds:frames */
    return num1*SAMPLES_PER_MINUTE + num2*SAMPLES_PER_SECOND + num3*SAMPLES_PER_FRAME;
}


const char * samplestostr(char * const buff, const size_t len, const samplenum_t samples)
{
    if (samples>MAX_SAMPLES)
    {
        return "overflow";
    }
    if (samples<0)
    {
        return "inf";
    }
    const unsigned min = samples / SAMPLES_PER_MINUTE;
    const unsigned sec = ( samples / SAMPLES_PER_SECOND ) % 60;
    const unsigned frm = ( samples / SAMPLES_PER_FRAME  ) % FRAMES_PER_SECOND;
    const unsigned smp = samples % SAMPLES_PER_FRAME;

    snprintf(buff, len, "%02u:%02u:%02u.%03u", min, sec, frm, smp);
    return buff;
}


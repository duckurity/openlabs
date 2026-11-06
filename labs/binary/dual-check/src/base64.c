#include <string.h>
#include "base64.h"

static const char b64_table[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static int b64_val(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

int b64_decode(const char *in, unsigned char *out, int out_size) {
    int len = (int)strlen(in);
    int out_len = 0;
    int val = 0, valb = -8;

    for (int i = 0; i < len; i++) {
        char c = in[i];
        if (c == '=') break;
        int d = b64_val(c);
        if (d == -1) continue;
        val = (val << 6) + d;
        valb += 6;
        if (valb >= 0) {
            if (out_len >= out_size) return -1;
            out[out_len++] = (unsigned char)((val >> valb) & 0xFF);
            valb -= 8;
        }
    }
    return out_len;
}

void b64_encode(const unsigned char *in, int len, char *out) {
    int o = 0;
    int i;
    for (i = 0; i + 2 < len; i += 3) {
        unsigned int triple = (in[i] << 16) | (in[i+1] << 8) | in[i+2];
        out[o++] = b64_table[(triple >> 18) & 0x3F];
        out[o++] = b64_table[(triple >> 12) & 0x3F];
        out[o++] = b64_table[(triple >> 6) & 0x3F];
        out[o++] = b64_table[triple & 0x3F];
    }
    int rem = len - i;
    if (rem == 1) {
        unsigned int triple = (in[i] << 16);
        out[o++] = b64_table[(triple >> 18) & 0x3F];
        out[o++] = b64_table[(triple >> 12) & 0x3F];
        out[o++] = '=';
        out[o++] = '=';
    } else if (rem == 2) {
        unsigned int triple = (in[i] << 16) | (in[i+1] << 8);
        out[o++] = b64_table[(triple >> 18) & 0x3F];
        out[o++] = b64_table[(triple >> 12) & 0x3F];
        out[o++] = b64_table[(triple >> 6) & 0x3F];
        out[o++] = '=';
    }
    out[o] = '\0';
}

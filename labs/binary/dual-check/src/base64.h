#ifndef BASE64_H
#define BASE64_H

// Decodes a null-terminated base64 string into out (caller-provided buffer).
// Returns number of bytes written, or -1 on error.
int b64_decode(const char *in, unsigned char *out, int out_size);

// Encodes len bytes from in into out as a null-terminated base64 string.
// out must be large enough: ((len+2)/3)*4 + 1 bytes.
void b64_encode(const unsigned char *in, int len, char *out);

#endif

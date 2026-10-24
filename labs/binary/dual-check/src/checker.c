// checker.c (v3 final)
// =========================================================================
// Compile with (MinGW on Windows):
//   gcc -o checker.exe checker.c aes.c sha256.c -Wall
//
// Flow the player must go through:
//
//   1) "Enter file password:" -- this is PASSWORD 2, the one revealed by
//      winning game.exe. Checked only against a stored SHA-256 hash, so
//      the real value is never sitting in this binary as plaintext.
//
//   2) "Enter the recovered hex value:" -- a 16-byte (32 hex char) value
//      that does NOT exist anywhere in this binary. The player must open
//      checker.exe in a disassembler, read compute_check_value() below,
//      and re-implement that exact chained transform themselves (e.g. in
//      a small Python script) to compute it from CHECK_SEED/CHECK_CONST.
//
//   3) Only if BOTH are correct does this program derive the final AES
//      key as fold(password2) XOR hexvalue, decrypt the embedded flag
//      ciphertext, and print it. Any wrong input at any step just prints
//      a generic failure -- there is no path that hands out the flag
//      without both values being genuinely correct.
// =========================================================================

#include <stdio.h>
#include <string.h>
#include "aes.h"
#include "sha256.h"

#define ROL8(x,n) ((unsigned char)(((x) << (n)) | ((x) >> (8-(n)))))

// ---- gate 1: password 2, checked only via hash ----
static const char *PW2_HASH_HEX =
    "f4e693b3a55f3e2097376c9a8f347b71831ae6a6b76f2da240b20e940711595b";

static int check_password2(const char *input) {
    char hex[65];
    sha256_hex(input, hex);
    return strcmp(hex, PW2_HASH_HEX) == 0;
}

// Folds an entire password string into a 16-byte key (every character
// matters, not just the first 16 bytes).
static void fold_password(const char *password, unsigned char *key_out) {
    memset(key_out, 0, 16);
    int len = (int)strlen(password);
    for (int i = 0; i < len; i++) {
        unsigned char c = (unsigned char)password[i];
        int idx = i % 16;
        key_out[idx] ^= c;
        key_out[idx] = (unsigned char)((key_out[idx] << 1) | (key_out[idx] >> 7));
    }
    key_out[len % 16] ^= (unsigned char)(len & 0xFF);
}

// ---- gate 2: a value the player must compute themselves ----
static const unsigned char CHECK_SEED[16] = {
    0x3f,0x8a,0x12,0xd4,0x67,0xe9,0x0b,0x55,
    0xc2,0x7a,0xf1,0x29,0x84,0x36,0xbd,0x5e
};
static const unsigned char CHECK_CONST[16] = {
    0x11,0x2d,0x3c,0x44,0x58,0x61,0x79,0x82,
    0x93,0xa5,0xb6,0xc8,0xd9,0xe2,0xf3,0x07
};

// Chained transform -- each byte depends on the previous result, so it
// must be replicated in order, byte by byte, not computed independently.
static void compute_check_value(unsigned char *out) {
    unsigned char prev = 0xA5;
    for (int i = 0; i < 16; i++) {
        unsigned char b = (unsigned char)(CHECK_SEED[i] ^ prev);
        b = ROL8(b, (i % 5) + 1);
        b ^= CHECK_CONST[i];
        b = (unsigned char)(b + (i * 3 + 7));
        out[i] = b;
        prev = b;
    }
}

// Parses exactly 32 hex characters into 16 bytes. Returns 0 on any
// malformed input (wrong length or non-hex characters).
static int parse_hex16(const char *str, unsigned char *out) {
    if (strlen(str) != 32) return 0;
    for (int i = 0; i < 16; i++) {
        unsigned int byte;
        if (sscanf(str + i * 2, "%2x", &byte) != 1) return 0;
        out[i] = (unsigned char)byte;
    }
    return 1;
}

// ---- the encrypted flag ----
static const unsigned char FLAG_IV[16] = {
    0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,
    0x39,0x3a,0x3b,0x3c,0x3d,0x3e,0x3f,0x40
};
static const unsigned char FLAG_CIPHERTEXT[48] = {
    0x13,0x14,0xd5,0x26,0x84,0xc8,0xb2,0xbe,
    0x9f,0x79,0x1f,0xeb,0x1f,0xe1,0x44,0x10,
    0x12,0xaa,0x79,0x9b,0xf1,0x61,0xc9,0x2b,
    0xcb,0xa2,0x9a,0x13,0x32,0x88,0xf0,0x7b,
    0x75,0xd5,0x9d,0xe7,0x4b,0x5c,0xa6,0x4d,
    0x61,0x0e,0xd3,0x45,0xfe,0x47,0x9d,0x54
};
#define FLAG_CIPHERTEXT_LEN 48

// Sanity check WITHOUT any literal flag-format string in the binary (no
// "duck{" string anywhere, so `strings`/static reading can't even see a
// hint of the flag format). Just checks the decrypted bytes are plausible
// printable text with a brace-style wrapper, using byte values instead of
// a string literal.
static int looks_like_flag(const unsigned char *buf, int len) {
    if (len < 6) return 0;
    if (buf[len - 1] != 0x7d) return 0; // '}'
    for (int i = 0; i < len; i++) {
        if (buf[i] < 0x20 || buf[i] > 0x7e) return 0; // must be printable
    }
    return 1;
}

int main(void) {
    char pw_input[128];
    char hex_input[128];

    printf("============================================================\n");
    printf(" checker.exe - Flag Verification Tool\n");
    printf("============================================================\n");

    printf("Enter file password: ");
    if (!fgets(pw_input, sizeof(pw_input), stdin)) return 1;
    pw_input[strcspn(pw_input, "\r\n")] = 0;

    if (!check_password2(pw_input)) {
        printf("\n[-] Incorrect password.\n");
        return 1;
    }
    printf("[+] Password accepted.\n\n");

    printf("Enter the recovered hex value: ");
    if (!fgets(hex_input, sizeof(hex_input), stdin)) return 1;
    hex_input[strcspn(hex_input, "\r\n")] = 0;

    unsigned char submitted[16];
    if (!parse_hex16(hex_input, submitted)) {
        printf("\n[-] Invalid hex value.\n");
        return 1;
    }

    unsigned char expected[16];
    compute_check_value(expected);
    if (memcmp(submitted, expected, 16) != 0) {
        printf("\n[-] Incorrect value. Keep reversing.\n");
        return 1;
    }

    // Both gates passed: derive the final key and decrypt the flag.
    unsigned char pw2_key[16];
    fold_password(pw_input, pw2_key);
    unsigned char final_key[16];
    for (int i = 0; i < 16; i++) final_key[i] = pw2_key[i] ^ submitted[i];

    unsigned char buf[FLAG_CIPHERTEXT_LEN];
    memcpy(buf, FLAG_CIPHERTEXT, FLAG_CIPHERTEXT_LEN);

    struct AES_ctx ctx;
    AES_init_ctx_iv(&ctx, final_key, FLAG_IV);
    AES_CBC_decrypt_buffer(&ctx, buf, FLAG_CIPHERTEXT_LEN);

    int pad = buf[FLAG_CIPHERTEXT_LEN - 1];
    int plain_len = FLAG_CIPHERTEXT_LEN - pad;
    if (pad < 1 || pad > 16 || plain_len < 0 || !looks_like_flag(buf, plain_len)) {
        printf("\n[-] Verification failed.\n");
        return 1;
    }

    buf[plain_len] = '\0';
    printf("\n[+] Correct! You have successfully solved the Reverse Engineering challenge.\n");
    printf("[+] FLAG: %s\n", buf);

    return 0;
}

// gen_checker_v3.c (DEV-ONLY generator, never ship this file or its .exe)
//
// Computes every embedded constant needed for the new checker.c:
//   - PW2_HASH_HEX      : SHA-256 hash of password 2 (the gate check)
//   - CHECK_SEED / CHECK_CONST : fixed arrays the player must read out of
//                          the binary and feed into their own re-implementation
//                          of compute_check_value() to get the hex value
//   - the resulting EXPECTED hex value (printed here only so we can verify
//     the chain logic once -- it is NOT embedded anywhere in checker.c;
//     checker.c recomputes it itself at runtime from CHECK_SEED/CHECK_CONST)
//   - FLAG_IV / FLAG_CIPHERTEXT : AES-128-CBC(flag) under the FINAL key,
//                          which is fold(password2) XOR hexvalue
//
// Build & run:
//   gcc -o gen_checker_v3 gen_checker_v3.c aes.c sha256.c -Wall
//   ./gen_checker_v3
#include <stdio.h>
#include <string.h>
#include "aes.h"
#include "sha256.h"

#define ROL8(x,n) ((unsigned char)(((x) << (n)) | ((x) >> (8-(n)))))

static const unsigned char CHECK_SEED[16] = {
    0x3f,0x8a,0x12,0xd4,0x67,0xe9,0x0b,0x55,
    0xc2,0x7a,0xf1,0x29,0x84,0x36,0xbd,0x5e
};
static const unsigned char CHECK_CONST[16] = {
    0x11,0x2d,0x3c,0x44,0x58,0x61,0x79,0x82,
    0x93,0xa5,0xb6,0xc8,0xd9,0xe2,0xf3,0x07
};

// Chained transform: each byte's result feeds into the next (CBC-like),
// so the player must replicate it in order, not independently per-byte.
static void compute_check_value(unsigned char *out) {
    unsigned char prev = 0xA5; // fixed initial chaining value
    for (int i = 0; i < 16; i++) {
        unsigned char b = (unsigned char)(CHECK_SEED[i] ^ prev);
        b = ROL8(b, (i % 5) + 1);
        b ^= CHECK_CONST[i];
        b = (unsigned char)(b + (i * 3 + 7));
        out[i] = b;
        prev = b;
    }
}

// Same key-folding function that will live in checker.c, used for password2.
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

static void print_array(const char *name, const unsigned char *buf, int len) {
    printf("static const unsigned char %s[%d] = {\n    ", name, len);
    for (int i = 0; i < len; i++) {
        printf("0x%02x", buf[i]);
        if (i != len - 1) printf(",");
        if ((i + 1) % 8 == 0) printf("\n    ");
    }
    printf("\n};\n\n");
}

int main(void) {
    const char *password2 = "ch3ck3r_unl0ck_key";
    const char *flag = "duck{...}";

    // ---- gate: SHA-256 hash of password2 ----
    char pw2_hash[65];
    sha256_hex(password2, pw2_hash);
    printf("PW2_HASH_HEX = \"%s\"\n\n", pw2_hash);

    print_array("CHECK_SEED", CHECK_SEED, 16);
    print_array("CHECK_CONST", CHECK_CONST, 16);

    // ---- compute expected hex value (NOT embedded, just for our own check) ----
    unsigned char hexval[16];
    compute_check_value(hexval);
    printf("# expected hex value (player must derive this, 32 hex chars):\n# ");
    for (int i = 0; i < 16; i++) printf("%02x", hexval[i]);
    printf("\n\n");

    // ---- final AES key = fold(password2) XOR hexval ----
    unsigned char pw2_key[16];
    fold_password(password2, pw2_key);
    unsigned char final_key[16];
    for (int i = 0; i < 16; i++) final_key[i] = pw2_key[i] ^ hexval[i];

    printf("# final AES key (fold(password2) XOR hexval) -- sanity only:\n# ");
    for (int i = 0; i < 16; i++) printf("%02x", final_key[i]);
    printf("\n\n");

    // ---- encrypt the flag under final_key ----
    const unsigned char iv[16] = {
        0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,
        0x39,0x3a,0x3b,0x3c,0x3d,0x3e,0x3f,0x40
    };
    int flen = (int)strlen(flag);
    int padded_len = ((flen / 16) + 1) * 16;
    unsigned char plain[128];
    memcpy(plain, flag, flen);
    int pad_val = padded_len - flen;
    for (int i = flen; i < padded_len; i++) plain[i] = (unsigned char)pad_val;

    struct AES_ctx ctx;
    AES_init_ctx_iv(&ctx, final_key, iv);
    AES_CBC_encrypt_buffer(&ctx, plain, padded_len);

    print_array("FLAG_IV", iv, 16);
    printf("static const unsigned char FLAG_CIPHERTEXT[%d] = {\n    ", padded_len);
    for (int i = 0; i < padded_len; i++) {
        printf("0x%02x", plain[i]);
        if (i != padded_len - 1) printf(",");
        if ((i + 1) % 8 == 0) printf("\n    ");
    }
    printf("\n};\n#define FLAG_CIPHERTEXT_LEN %d\n", padded_len);

    return 0;
}

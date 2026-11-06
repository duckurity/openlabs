// game.c (v3 - Medium difficulty)
// =========================================================================
// Compile with (MinGW on Windows):
//   gcc -o game.exe game.c base64.c -Wall
//
// Difficulty additions over v1:
//   1. Multi-byte repeating-key XOR (instead of a single fixed key byte)
//   2. The base64 string itself is stored additionally masked with a
//      constant byte, so it does NOT appear as readable text to a plain
//      `strings` scan -- it only becomes a valid base64 string after an
//      extra XOR step at runtime.
//   3. A basic anti-debugging check: if a debugger is attached while
//      verify_sys_integrity() runs, the password check always fails,
//      regardless of what is typed -- forcing pure static analysis
//      (or a debugger-bypass technique) instead of naive step-through.
//
// v3 change: PASSWORD_2 (needed for checker.exe) is no longer wrapped in
// AES -- it is hidden with the SAME multi-byte-XOR + masked-base64 scheme
// as PASSWORD_1, but with its own independent key and mask byte, so the
// player must repeat the same static-analysis technique a second time
// with different constants, rather than needing a separate crypto engine.
// This removes checker.exe's old dependency on AES-decrypting a value
// here -- checker.exe now verifies everything on its own.
// =========================================================================

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "base64.h"

#ifdef _WIN32
  #include <windows.h>
#else
  #include <sys/ptrace.h>
  #include <unistd.h>
#endif

// -------------------------------------------------------------------------
// Anti-debugging check.
// -------------------------------------------------------------------------
static int is_debugger_present(void) {
#ifdef _WIN32
    return IsDebuggerPresent() ? 1 : 0;
#else
    // Linux equivalent for cross-platform testing: a process can only be
    // ptrace-attached by one tracer at a time. If we can't trace
    // ourselves, something (e.g. gdb/strace) already is.
    if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) == -1) {
        return 1;
    }
    ptrace(PTRACE_DETACH, 0, NULL, NULL);
    return 0;
#endif
}

// -------------------------------------------------------------------------
// LAYER 1: multi-byte repeating-key XOR used to obfuscate PASSWORD_1
// before base64 encoding it.
// -------------------------------------------------------------------------
static const unsigned char XOR_KEY[] = { 0x4B, 0x33, 0x79, 0x21 }; // "K3y!"
#define XOR_KEY_LEN 4

static void xor_repeating(unsigned char *data, int len, const unsigned char *key, int key_len) {
    for (int i = 0; i < len; i++) data[i] ^= key[i % key_len];
}

// -------------------------------------------------------------------------
// LAYER 2: the base64 string is stored additionally masked with a
// constant byte (MASK_BYTE), so it is NOT a readable string in the
// compiled binary's data section -- a plain `strings` scan will not show
// valid base64 text here. It must first be unmasked with MASK_BYTE,
// THEN treated as base64, THEN XOR-decoded with the repeating key above.
// -------------------------------------------------------------------------
#define MASK_BYTE 0x01

// Masked bytes of: base64( xor_repeating("r3v3rs3_m3_pl2", XOR_KEY) )
// (precomputed; each byte here is the real base64 character XOR'd with
// MASK_BYTE, so this does NOT read as plain text in a hex/strings view)
// Trailing 0x00 is NOT part of the real data (only the first 20 bytes are
// used) -- it exists only so this symbol always has a null byte directly
// after its real content in memory, regardless of what the compiler places
// next. That stops Ghidra's decompiler from rendering this as a "merged"
// string with whatever string literal happens to follow it in .rdata.
static const unsigned char MASKED_B64[] = {
    0x4e,0x50,0x40,0x51,0x44,0x6b,0x6d,0x40,0x52,0x6f,0x35,0x6c,0x40,0x42,
    0x5b,0x53,0x4b,0x76,0x44,0x3c,
    0x00
};
#define MASKED_B64_LEN 20

// Intentionally unrelated function name, as before.
int verify_sys_integrity(const char *user_input) {
    // Anti-debug gate: if a debugger is attached, always reject -- no
    // matter what the user typed -- without any visible difference in
    // the printed error message.
    if (is_debugger_present()) {
        return 0;
    }

    unsigned char unmasked_b64[MASKED_B64_LEN + 1];
    for (int i = 0; i < MASKED_B64_LEN; i++) {
        unmasked_b64[i] = MASKED_B64[i] ^ MASK_BYTE;
    }
    unmasked_b64[MASKED_B64_LEN] = '\0';

    unsigned char decoded[64];
    int decoded_len = b64_decode((const char*)unmasked_b64, decoded, sizeof(decoded));
    if (decoded_len <= 0) return 0;

    xor_repeating(decoded, decoded_len, XOR_KEY, XOR_KEY_LEN);
    decoded[decoded_len] = '\0';

    return strcmp((char*)decoded, user_input) == 0;
}

// -------------------------------------------------------------------------
// Quiz: proves the player traced the RE steps. Updated to reflect the
// new multi-key XOR scheme.
// -------------------------------------------------------------------------
int run_quiz(void) {
    char answer[128];

    printf("\n--- Verification Quiz ---\n");
    printf("Answer based on what you found during your analysis.\n\n");

    printf("How many distinct XOR key bytes are used in the repeating key? (number)\n> ");
    if (!fgets(answer, sizeof(answer), stdin)) return 0;
    answer[strcspn(answer, "\n")] = 0;
    if (strcmp(answer, "4") != 0) {
        printf("\n[-] Incorrect. Access denied.\n");
        return 0;
    }

    printf("What are the 4 bytes of the XOR key, in hex, in order?\n");
    printf("(format: XX XX XX XX, spaces optional)\n> ");
    if (!fgets(answer, sizeof(answer), stdin)) return 0;
    answer[strcspn(answer, "\n")] = 0;
    {
        char normalized[64];
        int ni = 0;
        for (int i = 0; answer[i] != '\0' && ni < (int)sizeof(normalized) - 1; i++) {
            if (answer[i] == ' ') continue;
            char c = answer[i];
            if (c >= 'a' && c <= 'z') c = (char)(c - 'a' + 'A');
            normalized[ni++] = c;
        }
        normalized[ni] = '\0';
        if (strcmp(normalized, "4B337921") != 0) {
            printf("\n[-] Incorrect. Access denied.\n");
            return 0;
        }
    }

    printf("What is the name of the function that verifies the password?\n> ");
    if (!fgets(answer, sizeof(answer), stdin)) return 0;
    answer[strcspn(answer, "\n")] = 0;
    if (strcmp(answer, "verify_sys_integrity") != 0) {
        printf("\n[-] Incorrect. Access denied.\n");
        return 0;
    }

    return 1;
}

// -------------------------------------------------------------------------
// Mini-game: unchanged from v1.
// -------------------------------------------------------------------------
int run_mini_game(void) {
    char answer[16];
    int secret_number = 7;

    printf("\n--- Final Step: Mini Game ---\n");
    printf("Guess the secret number (1-10). You have 3 attempts.\n");

    for (int attempt = 1; attempt <= 3; attempt++) {
        printf("Attempt %d/3 > ", attempt);
        if (!fgets(answer, sizeof(answer), stdin)) return 0;
        if (atoi(answer) == secret_number) {
            printf("[+] Correct guess!\n");
            return 1;
        }
        printf("Wrong, try again.\n");
    }
    return 0;
}

// -------------------------------------------------------------------------
// PASSWORD_2 (v3): hidden with the same technique as PASSWORD_1 -- a
// multi-byte repeating XOR key, then base64, then the base64 text itself
// masked with a constant byte -- but using its OWN independent key and
// mask so it is not just a copy of the password 1 constants.
// -------------------------------------------------------------------------
static const unsigned char XOR_KEY_2[] = { 0x7A, 0x1C, 0x93 };
#define XOR_KEY_2_LEN 3
#define MASK_BYTE_2 0x5A

// Same trailing-0x00 trick as MASKED_B64 above, for the same reason.
static const unsigned char MASKED_B64_2[] = {
    0x1d,0x02,0x09,0x3d,0x1d,0x02,0x3f,0x3d,0x19,0x1f,0x0a,0x37,
    0x1c,0x12,0x19,0x30,0x1d,0x02,0x3c,0x17,0x1f,0x02,0x34,0x2b,
    0x00
};
#define MASKED_B64_2_LEN 24

void reveal_password_2(char *out, int out_size) {
    unsigned char unmasked_b64[MASKED_B64_2_LEN + 1];
    for (int i = 0; i < MASKED_B64_2_LEN; i++) {
        unmasked_b64[i] = MASKED_B64_2[i] ^ MASK_BYTE_2;
    }
    unmasked_b64[MASKED_B64_2_LEN] = '\0';

    unsigned char decoded[64];
    int decoded_len = b64_decode((const char*)unmasked_b64, decoded, sizeof(decoded));
    if (decoded_len <= 0) { out[0] = '\0'; return; }

    xor_repeating(decoded, decoded_len, XOR_KEY_2, XOR_KEY_2_LEN);

    if (decoded_len >= out_size) decoded_len = out_size - 1;
    memcpy(out, decoded, decoded_len);
    out[decoded_len] = '\0';
}

// -------------------------------------------------------------------------
// Main flow
// -------------------------------------------------------------------------
int main(void) {
    char input[128];
    char password2[64];

    printf("============================================================\n");
    printf(" Welcome. Enter the password to continue.\n");
    printf("============================================================\n");
    printf("Password: ");
    if (!fgets(input, sizeof(input), stdin)) return 1;
    input[strcspn(input, "\n")] = 0;

    if (!verify_sys_integrity(input)) {
        printf("[-] Incorrect password. Goodbye.\n");
        return 1;
    }
    printf("\n[+] Password accepted.\n");

    if (!run_quiz()) {
        printf("[-] Quiz failed. Goodbye.\n");
        return 1;
    }
    printf("\n[+] Quiz passed!\n");

    if (!run_mini_game()) {
        printf("[-] Mini-game failed. Goodbye.\n");
        return 1;
    }

    printf("\n[+] You won the mini-game, but this is not the end...\n");
    reveal_password_2(password2, sizeof(password2));
    printf("[i] Here is a password you will need for the NEXT file (checker.exe):\n\n");
    printf("    %s\n", password2);
    printf("\n[i] checker.exe is a completely separate file. It does not run\n");
    printf("    or read anything from this program. Open it on its own and\n");
    printf("    reverse-engineer it from scratch -- this password only gets\n");
    printf("    you past its first prompt.\n");

    return 0;
}

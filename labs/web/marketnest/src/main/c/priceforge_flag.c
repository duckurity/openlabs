#include <stdio.h>
#include <stddef.h>

/*
 * The flag is intentionally stored as XOR-obfuscated bytes in a native
 * executable instead of as a readable file.  The challenge's RCE must find
 * and execute this helper to make the flag appear on stdout.
 */
int main(void) {
    static const unsigned char encoded[] = {
        62, 47, 57, 49, 33, 48, 49, 47, 5, 107, 52, 48, 105, 57, 46, 107,
        106, 52, 5, 46, 106, 5, 41, 42, 105, 22, 5, 107, 52, 48, 105, 57,
        46, 107, 106, 52, 5, 40, 57, 105, 5, 61, 40, 110, 52, 46, 105, 62,
        5, 106, 107, 104, 34, 59, 48, 62, 39
    };

    for (size_t i = 0; i < sizeof(encoded); ++i) {
        putchar(encoded[i] ^ 0x5A);
    }
    putchar('\n');
    return 0;
}

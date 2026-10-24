#include <stdio.h>
#include <string.h>
#include "sha256.h"

int main() {
    char hex[65];
    int all_pass = 1;

    const char *empty_expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    const char *abc_expected   = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

    sha256_hex("", hex);
    printf("SHA256('') = %s\n", hex);
    printf("Expected   = %s\n", empty_expected);
    printf("%s\n\n", strcmp(hex, empty_expected) == 0 ? "[PASS]" : "[FAIL]");
    if (strcmp(hex, empty_expected) != 0) all_pass = 0;

    sha256_hex("abc", hex);
    printf("SHA256('abc') = %s\n", hex);
    printf("Expected      = %s\n", abc_expected);
    printf("%s\n\n", strcmp(hex, abc_expected) == 0 ? "[PASS]" : "[FAIL]");
    if (strcmp(hex, abc_expected) != 0) all_pass = 0;

    const char *longmsg = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    const char *long_expected = "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1";
    sha256_hex(longmsg, hex);
    printf("SHA256(56-char msg) = %s\n", hex);
    printf("Expected            = %s\n", long_expected);
    printf("%s\n\n", strcmp(hex, long_expected) == 0 ? "[PASS]" : "[FAIL]");
    if (strcmp(hex, long_expected) != 0) all_pass = 0;

    printf("==================\n");
    printf("%s\n", all_pass ? "ALL TESTS PASSED" : "SOME TESTS FAILED");
    return all_pass ? 0 : 1;
}

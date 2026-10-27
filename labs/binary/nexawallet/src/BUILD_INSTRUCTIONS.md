# Build Instructions

Builds with **Android Studio** (any recent version with Android Gradle Plugin support for `compileSdk 34`). Requires the Android SDK; no other external dependencies beyond what Gradle resolves automatically (AndroidX, Material Components, OkHttp).

## 1. Open the project

```
File → Open → select:
<repo root>/Mobile CTF Challenge (v2 Design)/
```

Open that folder specifically — not the repo root, and not the sibling `(v1 Design)` folder.

## 2. Let Gradle sync

First sync needs internet access to resolve dependencies and, if not already cached locally, the Gradle wrapper itself. No manual configuration is required beyond what Android Studio prompts for (an SDK location in `local.properties`, created automatically on first open).

## 3. Build

```
Build → Rebuild Project
```

or from a terminal in that folder:

```
./gradlew assembleDebug
```

Output APK:

```
app/build/outputs/apk/debug/app-debug.apk
```

Copy this into `../bin/` (see `../bin/README.md`) and rename it to `NexaWallet-debug.apk` for distribution.

## 4. Run / test environment for solving

- Any Android emulator (API 24+) or physical device works for *playing* the app normally.
- To **solve** it (reproduce the Walkthrough), you additionally need:
  - Root or an emulator image that allows running a `frida-server` binary matching the device's ABI (check with `adb shell getprop ro.product.cpu.abi`).
  - `frida-tools` installed on the host machine, matching the `frida-server` version running on the device.
- No special build flags, signing, or environment variables are required — the challenge logic is identical in debug and would remain identical in a signed release build.

## Notes

- `minifyEnabled` is currently `false` for easier verification during development; enabling R8/ProGuard before distributing to participants is optional hardening (see `docs/remediation.mdx`) and does not change the solve path, only the effort needed to read the decompiled code.
- There is no backend server for this challenge — all persistence (`LocalLedger`) is local `SharedPreferences`, reset by uninstalling the app.

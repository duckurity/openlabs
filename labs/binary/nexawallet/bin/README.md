# bin/ — playable challenge file

This folder should contain the installable APK handed to participants:

```
NexaWallet-debug.apk
```

## Where to get it

The APK isn't checked into this folder directly (it's a build output, not source). To produce it:

1. Follow `../src/BUILD_INSTRUCTIONS.md` to open and build the project in Android Studio.
2. After a successful `Build → Rebuild Project` / `assembleDebug`, the output lands at:
   ```
   Mobile CTF Challenge (v2 Design)/app/build/outputs/apk/debug/app-debug.apk
   ```
3. Copy that file into this folder and rename it to `NexaWallet-debug.apk` (or whatever filename the task tracker expects).

## Install command (for reference in the Walkthrough)

```
adb install -r NexaWallet-debug.apk
```

No signing, no obfuscation pass, and no backend server are required — the app is fully self-contained and runs standalone on any emulator or device with Android 7.0 (API 24) or newer.

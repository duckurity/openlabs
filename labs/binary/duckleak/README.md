# duckleak

`easy` · `binary`

## Brief

DuckCorp ships NestGuard, an internal Android app for staff. It keeps a vault of private files and a staff discount behind a PIN. The developer shipped the build in a hurry. Download the APK and open the vault.

## Setup

Run these from the lab directory:

```bash
docker compose up -d
```

Open `http://localhost:8080` and download `duckleak.apk`. Install it on an Android emulator or device:

```bash
adb install duckleak.apk
```

You need a decompiler such as JADX. Static analysis of the APK is enough for a full solve. Running the app needs an emulator or device plus adb (Android platform-tools).

## Goal

Unlock the vault, reach the employee discount, and recover the flag. Verify the solve from the lab directory:

```bash
python3 ../../../scripts/check.py .
```

See [how to play](/play) for the usual solve loop.

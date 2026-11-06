# src/ — source code location

The full, buildable Android Studio project for this challenge is **not included in this repository yet**. It currently exists only in the author's local development environment as its own complete Gradle project (`Mobile CTF Challenge (v2 Design)/`).

Only the pre-built `bin/NexaWallet-debug.apk` is distributed here — that is all participants ever need, since this is a BYOD artifact lab with no server-side component.

> **TODO (maintainers):** the source tree needs to be added to this repository (e.g. under `labs/binary/nexawallet/src/android-project/`) before any future rebuild or patch of the APK is possible from a clean clone. Until then, changes to the challenge logic require the original author's local project.

> **Reminder:** once added, this source tree is for internal/organizer use only — never ship it to participants.

## Source layout (for reference)

This reflects the structure of the author's local project, reproduced here for documentation purposes until the source itself is committed:

```
Mobile CTF Challenge (v2 Design)/app/src/main/java/com/example/nexawallet/
├── integrity/
│   └── IntegrityGate.kt           Gate 1 — unified Frida detection
├── authorization/
│   ├── ReviewState.kt             Gate 2 — clearance state
│   └── TransferAuthorizer.kt      limit check + clearance check + flag minting
├── session/
│   └── UserSession.kt             login/session state only
├── data/
│   └── LocalLedger.kt             local mock backend (balance, limit, accounts)
├── ui/
│   ├── LoginActivity.kt / RegisterActivity.kt / HomeActivity.kt
│   ├── TransferActivity.kt        main challenge screen
│   ├── WebTransferActivity.kt
│   ├── RestrictedActivity.kt      shown when Gate 1 fails
│   └── ReviewGateActivity.kt      the hidden screen (Gate 2)
└── network/
    ├── PinningConfig.kt
    └── WebViewTrustManager.kt
```

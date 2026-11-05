# DuckWebView — Validation and Testing

## 1. Clean Environment Validation
Stop any existing challenge containers:

```bash
docker compose down --remove-orphans
```

Build and start the backend:

```bash
docker compose up --build -d
```

Confirm the container is running:

```bash
docker compose ps
```

Inspect recent logs:

```bash
docker compose logs --tail 100 duckwebview
```

The backend should be reachable at:

```text
http://localhost:8080
```

Health check:

```text
http://localhost:8080/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## 2. Android APK Validation
Verify the following:
- [ ] Gradle Sync completes successfully.
- [ ] The debug APK builds successfully.
- [ ] The APK installs on the selected Android emulator or test device.
- [ ] The application launches without crashing.
- [ ] The archive preview interface is displayed.
- [ ] The default HTML preview renders successfully.
- [ ] The preview field accepts user-supplied HTML.
- [ ] The APK contains `assets/archive_catalog.json`.


## 3. Android APK Build and Integrity
- Build variant: Debug
- Build command: `gradlew.bat assembleDebug`
- Android application ID: `com.duckurity.duckwebview`
- Minimum SDK: 23
- Target SDK: 35
- APK artifact: `src/static/downloads/duckwebview.apk`
- SHA-256: `12520a3d0ac02a2cd246fb17aa0889b49460017e390721e2010de92de2712281`

The SHA-256 value was calculated from the APK artifact
copied to the repository's download directory.


## 4. Static Analysis Validation
Inspect the APK using JADX or an equivalent tool.

Verify the following:
- [ ] `MainActivity` can be located.
- [ ] JavaScript enablement can be identified.
- [ ] The `DuckBridge` interface can be identified.
- [ ] The `getArchiveStatus` method can be identified.
- [ ] The `openArchiveRecord` method can be identified.
- [ ] The archive catalog can be located.
- [ ] The Base64 archive record ID can be decoded.
- [ ] The Base64 access code can be decoded.
- [ ] The configured challenge flag is not embedded in the APK source or assets.

Expected decoded metadata:

```text
ARCHIVE-07
7391
```

## 5. Backend Validation
Verify that the backend starts with a configured `FLAG`.

Request the health endpoint:

```bash
curl http://localhost:8080/health
```

Expected response:

```json
{
  "status": "ok"
}
```

Request an archive challenge nonce:

```bash
curl http://localhost:8080/api/archive/challenge
```

Expected behavior:
- A nonce is returned.
- The response contains an expiration interval.
- The nonce is accepted only once.
- Expired or reused nonces are rejected.

## 6. Intended Vulnerability Validation

Install and launch the APK.

Enter the following payload in the HTML preview field:

```html
<script>
alert(
    DuckBridge.openArchiveRecord(
        "ARCHIVE-07",
        "7391"
    )
);
</script>
```

Tap **Preview HTML**.

Expected behavior:
- The JavaScript invokes the exposed bridge method.
- The bridge requests a nonce from the backend.
- The bridge submits the archive request.
- The backend validates the nonce and archive parameters.
- A successful response contains the configured challenge flag.

## 7. Invalid Input Validation
Test the bridge with incorrect archive parameters.

Expected behavior:
- Invalid record IDs are rejected by the native bridge.
- Invalid access codes are rejected by the native bridge.
- No successful archive response is returned for invalid parameters.

Test the backend with missing or invalid fields.

Expected behavior:
- Malformed JSON is rejected.
- Missing nonce values are rejected.
- Invalid or expired nonces are rejected.
- Reused nonces are rejected.
- Invalid archive credentials are rejected.
- Failed requests do not return the flag.

## 8. Alternate-Path Assessment

Test whether the archive backend can be called directly without invoking the Android application.

Verify the following:
- [ ] The nonce endpoint can be reached from the intended local environment.
- [ ] The query endpoint rejects missing nonces.
- [ ] The query endpoint rejects invalid and reused nonces.
- [ ] Direct API requests have been tested and documented.
- [ ] Any alternate path to the flag is recorded accurately.

A single-use nonce does not prove that a request originated from the WebView. Do not mark the direct API path as blocked unless it has been tested and the implementation supports that conclusion.

## 9. Flag Retrieval Validation
Confirm that the successful intended workflow returns the configured flag.

Expected format:

```text
duck{...}
```

Verify that:
- [ ] The flag comes from the backend configuration.
- [ ] The flag is not hardcoded in the APK.
- [ ] The flag is returned only after successful backend validation.
- [ ] The flag matches the value configured for the local test environment.

## 10. Reset Validation

Reset the backend:

```bash
docker compose down --remove-orphans
docker compose up --build -d
```

Repeat:
1. Health check.
2. APK launch.
3. Archive metadata inspection.
4. Bridge payload execution.
5. Flag retrieval.
6. Invalid input tests.

The challenge should behave consistently after the backend restarts.

## 11. Final Submission Checklist
- [ ] The Android APK builds successfully.
- [ ] The application launches without crashing.
- [ ] The archive preview works.
- [ ] The archive catalog is included in the APK.
- [ ] The Base64 values can be decoded.
- [ ] The exposed JavaScript bridge can be identified.
- [ ] The intended HTML payload invokes the bridge.
- [ ] The backend starts using the documented instructions.
- [ ] The configured flag is not embedded in the APK.
- [ ] Valid archive requests return the configured flag.
- [ ] Invalid requests are rejected.
- [ ] Nonce expiration and reuse behavior are tested.
- [ ] Direct API access has been assessed.
- [ ] The intended attack path is documented.
- [ ] Maintainer-only solution files are excluded from the participant bundle.
- [ ] All validation results reflect tests that were actually performed.

Only mark a check as passed after executing it against the final build.
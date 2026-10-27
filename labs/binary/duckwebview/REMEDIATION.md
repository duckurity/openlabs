# DuckWebView — Remediation Documentation

## Vulnerability

Insecure WebView JavaScript Bridge exposure to user-controlled HTML.

Affected component:

```text
com.duckurity.duckwebview.MainActivity
```

Relevant functionality:

```text
DuckBridge.openArchiveRecord(recordId, accessCode)
```

---

## Root Cause
The application enables JavaScript in a WebView and exposes native application functionality through `addJavascriptInterface`.

The WebView also renders user-controlled HTML. As a result, JavaScript within that content can invoke exposed native methods.

The application does not establish an adequate trust boundary between untrusted HTML and sensitive native functionality.

---

## Vulnerable Pattern
Conceptually, the vulnerable design resembles:

```java
webView.getSettings().setJavaScriptEnabled(true);

webView.addJavascriptInterface(
    new ArchiveBridge(),
    "DuckBridge"
);
```

The application subsequently loads user-controlled HTML into the same WebView.

This combination allows the loaded JavaScript to invoke methods exposed through the bridge.

---

## Recommended Fix

### 1. Avoid Exposing Privileged Native Methods
Do not expose sensitive native functionality to WebView content that is not fully trusted.

Where a JavaScript bridge is necessary, minimize its exposed methods and the privileges available through those methods.

Removing the bridge is preferable when the application does not require it.

---

### 2. Restrict WebView Content
Avoid loading attacker-controlled HTML into a WebView that has access to privileged native methods.

Where applicable:
- Load only trusted content.
- Restrict navigation to expected destinations.
- Prevent untrusted redirects and content from reaching privileged WebViews.
- Use a separate WebView without a native bridge for untrusted content.

Origin restrictions are useful defense-in-depth measures, but they do not make an otherwise unsafe bridge secure.

---

### 3. Do Not Trust Client-Side Validation
The archive record ID and access code are stored in the APK as Base64-encoded values.

Base64 is not encryption. Values stored in an APK should be treated as discoverable by a participant or attacker.

Client-side validation may improve application behavior, but it must not be treated as a security boundary.

The backend must independently enforce authorization.

---

### 4. Strengthen Backend Authorization
The backend should validate each archive request and ensure that the requester is authorized to access the requested record.

A nonce can help prevent replay of a previously issued request when implemented correctly, but it does not prove that a request originated from a trusted WebView.

Do not use a nonce alone as proof of client trust.

Avoid returning sensitive information merely because a request contains values recovered from the APK.

---

### 5. Protect Sensitive Data
The challenge flag should be configured outside the Android application.

Recommended controls:
- Keep the flag on the backend.
- Do not embed the flag in Java source files.
- Do not include the flag in APK assets.
- Do not place populated `.env` files in public repositories.
- Inject the challenge flag through the platform's supported runtime configuration.

---

### 6. Secure Network Communication
Use HTTPS for backend communication outside isolated local development environments.

Avoid relying on cleartext HTTP in production configurations.

Ensure that the backend address and network configuration are appropriate for the deployment environment.

---

### 7. Input Validation and Error Handling
Validate archive parameters on the backend.

The backend should:
- Reject malformed requests.
- Reject invalid archive identifiers and access codes.
- Reject missing, invalid, expired, or reused nonces.
- Avoid returning sensitive data in error responses.
- Log relevant security events without exposing the challenge flag in unnecessary logs.

Input validation complements authorization but does not replace it.

---

## Required Security Controls
The following controls should be applied:
- **Native bridge minimization:** expose only functionality that is strictly necessary.
- **WebView isolation:** separate untrusted content from privileged application functionality.
- **Backend authorization:** enforce access controls independently of client-side checks.
- **Secret management:** keep the flag outside the APK.
- **Replay protection:** use short-lived, single-use nonces where appropriate.
- **Secure transport:** use HTTPS outside local isolated development.
- **Regression testing:** verify that untrusted HTML cannot invoke privileged functionality after remediation.

---

## Verification and Retest
After remediation, verify the following.

### Normal Application Behavior
The application should launch and display its expected interface.

### WebView Bridge
Untrusted HTML should not be able to invoke privileged native methods.

### Archive Authorization
The backend should independently authorize archive requests.

### Sensitive Data
The APK should not contain the configured challenge flag.

### Regression Tests
Retest the original HTML payload and confirm that it no longer retrieves the flag through unauthorized bridge access.

### Alternate Access Paths
Test the backend directly to identify any alternative route to sensitive data. Document actual behavior rather than assuming that requests must originate from the Android application.

---

## Secure Behavior
After remediation:
- Untrusted HTML cannot invoke privileged native functionality.
- Sensitive archive operations require backend authorization.
- The challenge flag remains outside the APK.
- Nonce validation behaves as intended.
- Direct API access is assessed independently.
- Security tests verify the trust boundary between WebView content and native application code.
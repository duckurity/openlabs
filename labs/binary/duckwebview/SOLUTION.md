# DuckWebView — Official Solution and Security Report

## 1. Executive Summary
DuckWebView is a controlled Android Capture The Flag challenge designed to demonstrate the security risks associated with insecure WebView configurations and exposed JavaScript interfaces.

The application enables JavaScript within a WebView and allows user-controlled HTML to be rendered. It also exposes a native JavaScript interface named `DuckBridge`, which provides access to archive functionality.

The intended attack path requires participants to inspect the APK, enumerate application assets, decode the archive metadata, identify the exposed bridge methods, construct an HTML payload, and invoke the native archive workflow to retrieve the challenge flag.

### Primary Vulnerability
Insecure WebView JavaScript Bridge exposure to user-controlled HTML.

### Security Impact
An attacker who can control the HTML rendered by the WebView may invoke exposed native functionality without an adequate trust boundary between untrusted content and privileged application code.

The demonstrated impact is unauthorized invocation of archive functionality and retrieval of the challenge flag.

### Learning Objectives
The challenge is intended to teach participants how to:
- Inspect an Android APK using static-analysis tools.
- Enumerate application assets.
- Decode Base64-encoded data.
- Identify JavaScript-enabled WebViews.
- Discover methods exposed through `addJavascriptInterface`.
- Understand the security boundary between JavaScript and native Android code.
- Construct an HTML payload that invokes an exposed native method.
- Analyze the interaction between an Android application and a backend service.

---

## 2. Challenge Overview

### Challenge Name

DuckWebView

### Application Functionality
The application provides an HTML preview interface inside an Android WebView.

The relevant components include:

- `MainActivity`
- `WebView`
- `DuckBridge`
- `assets/archive_catalog.json`
- The archive backend

The archive catalog contains Base64-encoded archive metadata. The native bridge uses the decoded values when processing an archive request.

The challenge flag is configured on the backend and is not intended to be embedded in the APK.

### Scenario
DuckWebView is a legacy archive preview application. The application exposes native functionality to JavaScript while allowing the user to control the HTML rendered in the WebView.

Participants must investigate the application and determine whether this trust boundary can be abused.

### Primary Vulnerability
Insecure WebView JavaScript Bridge exposure.

### Secondary Vulnerability
No separate secondary vulnerability is intentionally required by the challenge.

The encoded archive metadata is an enumeration step rather than an independent vulnerability.

### Difficulty

Medium.

The intended solution combines several investigation and exploitation steps:
1. APK enumeration.
2. Asset inspection.
3. Base64 decoding.
4. Native-code inspection.
5. JavaScript bridge discovery.
6. HTML payload construction.
7. Native method invocation.
8. Backend interaction.
9. Challenge flag retrieval.

### Estimated Solve Time

Approximately 20–45 minutes for a participant familiar with Android application analysis, JADX, HTML, and JavaScript.

This is an estimate, not a guaranteed completion time.

---

## 3. Architecture and Trust Boundaries

### Components

The challenge consists of:
- An Android application that renders user-controlled HTML.
- A WebView with JavaScript enabled.
- A JavaScript interface named `DuckBridge`.
- An archive catalog bundled in the APK.
- A backend that validates archive requests and returns the configured flag.

### Application Flow

```text
Participant
    |
    | Analyze APK
    v
Android Application
    |
    | Inspect archive catalog
    | Decode Base64 values
    v
MainActivity
    |
    | Load user-controlled HTML
    v
WebView
    |
    | JavaScript calls DuckBridge
    v
Native ArchiveBridge
    |
    | Request nonce and submit archive request
    v
Archive Backend
    |
    | Validate request
    v
Challenge Flag
```

### Trust Boundaries
The relevant trust boundaries are:
1. Participant-controlled HTML entering the WebView.
2. JavaScript executing inside the WebView.
3. JavaScript invoking native methods through `DuckBridge`.
4. Native application code communicating with the archive backend.
5. The backend validating archive requests before returning the flag.

The intended vulnerability occurs at the boundary between user-controlled WebView content and native application functionality.

---

## 4. Attacker Starting Point
The participant starts with access to the Android APK.

No source code is required to begin the challenge.

### Initial Capabilities
The participant can:
- Install and run the application.
- Inspect the APK using static-analysis tools.
- Examine bundled assets.
- Interact with the HTML preview field.

The participant is not provided with the challenge flag.

---

## 5. Attack Surface

### Android Application
The relevant application components are:

```text
com.duckurity.duckwebview.MainActivity
```

The application loads HTML into a WebView and exposes a JavaScript interface.

### WebView Configuration
The relevant behavior includes:

- JavaScript enabled through WebView settings.
- User-controlled HTML rendered using `loadDataWithBaseURL`.
- A JavaScript interface registered under the name `DuckBridge`.

### JavaScript Bridge
The relevant exposed methods are:

```text
DuckBridge.getArchiveStatus()
DuckBridge.openArchiveRecord(recordId, accessCode)
```

### Archive Catalog
The following asset is relevant:

```text
assets/archive_catalog.json
```

It contains the encoded archive record ID and access code.

### Backend
The Android application's development configuration communicates with the archive service through the host machine's published port.

The backend exposes endpoints for obtaining a short-lived nonce and submitting an archive request.

---

## 6. Vulnerability Description

### Vulnerability Type
Insecure WebView JavaScript Bridge.

### Affected Component

```text
com.duckurity.duckwebview.MainActivity
```

Specifically, the WebView configuration and the `ArchiveBridge` implementation.

### Preconditions
The intended exploitation path requires the participant to:
1. Obtain and install the APK.
2. Inspect the application and its assets.
3. Recover the archive metadata.
4. Identify the exposed bridge method.
5. Supply HTML that invokes the native method.
6. Have the archive backend running and configured with a challenge flag.

### Failed Security Control

The application exposes a native interface to HTML that the user can control.

The bridge does not establish that the calling content is trusted before performing the archive operation.

### Technical Root Cause

The application enables JavaScript and registers a native Java object using `addJavascriptInterface`.

Conceptually, the vulnerable design resembles:

```java
webView.getSettings().setJavaScriptEnabled(true);

webView.addJavascriptInterface(
    new ArchiveBridge(),
    "DuckBridge"
);
```

The application subsequently loads user-controlled HTML into that WebView.

As a result, JavaScript in the loaded HTML can invoke methods exposed by the native bridge.

### Archive Metadata

The archive catalog stores encoded values such as:

```json
{
  "archive_ref_b64": "QVJDSElWRS0wNw==",
  "access_code_b64": "NzM5MQ==",
  "note": "Archive metadata is encoded with Base64."
}
```

The encoded values can be decoded to recover the archive parameters.

Base64 is encoding, not encryption, and does not protect confidential values.

---

## 7. Intended Attack Path

### Step 1 — Inspect the APK
Open the APK using JADX or an equivalent Android static-analysis tool.

Locate `MainActivity` and inspect the application initialization and WebView configuration.

Identify the JavaScript enablement and the registration of the `DuckBridge` interface.

### Step 2 — Enumerate Application Assets

Locate:

```text
assets/archive_catalog.json
```

Inspect its fields and identify the Base64-encoded archive metadata.

### Step 3 — Decode the Archive Metadata
The expected decoded values are:

```text
Archive Record ID: ARCHIVE-07
Access Code: 7391
```

For example, these values can be decoded using a Base64 decoder or a short script.

### Step 4 — Identify the Exposed Native Method

Inspect `ArchiveBridge` and identify:

```text
openArchiveRecord(String recordId, String accessCode)
```

Determine how the method validates the archive parameters and communicates with the backend.

### Step 5 — Construct the HTML Payload
Enter the following HTML into the application's preview field:

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

### Step 6 — Execute the Payload
Tap **Preview HTML**.

The JavaScript invokes the exposed native bridge method. The bridge requests a nonce from the backend, submits the archive parameters, and returns the backend response.

### Step 7 — Verify the Result
Confirm that the response contains:

```text
"status": "success"
```

and the configured challenge flag.

The expected flag format is:

```text
duck{...}
```

Capture evidence of the decoded metadata, the bridge method, the HTML payload, and the successful response.

---

## 8. Impact Assessment

### Confidentiality
The challenge demonstrates unauthorized access to a sensitive archive operation through a native method exposed to user-controlled HTML.

The successful attack retrieves the challenge flag.

### Integrity
No integrity impact is intentionally demonstrated.

### Availability
No availability impact is intentionally demonstrated.

### Privileges and Data Access

The intended attack does not require Android operating-system privilege escalation or remote code execution.

The demonstrated issue is the ability to invoke exposed native application functionality through untrusted WebView content.

---

## 9. Flag Retrieval

### Required Condition
The intended path requires successful invocation of the exposed bridge method with the archive parameters and a functioning backend.

### Flag Location
The flag is configured on the backend through the `FLAG` environment variable.

It is not intended to be hardcoded in `MainActivity.java` or the APK assets.

### Evidence of Successful Exploitation

Successful exploitation returns a backend response containing the challenge flag.

The flag follows this format:

```text
duck{...}
```

### Alternate-Path Limitation
The backend issues short-lived, single-use nonces, but the nonce mechanism does not prove that a request originated from the Android WebView.

A participant who reverse-engineers the request protocol may be able to request a nonce and call the backend directly.

Therefore, the intended learning objective is exploitation of the insecure WebView bridge, but the implementation does not guarantee that this is the only route to the flag.

---

## 10. Root Cause
The root cause is the exposure of native application functionality to untrusted WebView content.

The application combines JavaScript execution, user-controlled HTML, and a privileged native interface without a sufficient trust boundary.

The bridge therefore permits untrusted content to invoke functionality that should not be available to arbitrary HTML.

---

## 11. Remediation
The application should avoid exposing sensitive native functionality to untrusted WebView content.

Recommended controls include:
- Avoid `addJavascriptInterface` for content that is not fully trusted.
- Do not render attacker-controlled HTML in a WebView that exposes privileged native methods.
- Restrict WebView navigation and content loading to trusted sources where applicable.
- Do not treat Base64 encoding as a security mechanism.
- Keep sensitive values on the backend.
- Enforce authorization on the backend independently of client-side checks.
- Use HTTPS for communication outside isolated local development.
- Avoid assuming that a request originated from a trusted WebView merely because the application normally makes that request.

---

## 12. Verification and Retest
After remediation, verify the following.

### Normal Functionality
The application should launch and render the default preview.

### Bridge Exposure
Untrusted HTML should not be able to invoke privileged native functionality.

### Archive Access
Archive access should be authorized by the backend independently of client-side validation.

### Sensitive Data
The APK should not contain the actual configured challenge flag.

### Regression Testing
Retest the intended payload and verify that it no longer permits unauthorized archive access after remediation.

---

## 13. Unintended Attack Paths
The challenge is intended to focus on the WebView-to-native trust boundary.

The following observations should be checked during validation:
- Whether the flag is accidentally embedded in the APK.
- Whether the archive API can be called directly.
- Whether invalid archive parameters are rejected.
- Whether expired and reused nonces are rejected.
- Whether the backend can be reached without using the Android application.

The current nonce design is not a guarantee against direct API use. Any alternate route discovered during testing should be documented accurately.

---

## 14. Conclusion
DuckWebView demonstrates how insecure WebView configuration can expose native application functionality to untrusted HTML.

The intended solution combines APK inspection, asset enumeration, Base64 decoding, native-code analysis, JavaScript bridge discovery, and exploitation.

The primary security lesson is that WebView-to-native interfaces must be treated as security-sensitive boundaries. Client-side checks and encoded data do not replace appropriate trust and authorization controls.
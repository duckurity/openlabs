package com.duckurity.duckwebview;

import android.app.Activity;
import android.os.Bundle;
import android.text.InputType;
import android.util.Base64;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {

    private static final String API_BASE =
            "http://10.0.2.2:8080";

    private WebView webView;
    private EditText htmlInput;

    private String expectedRecordId;
    private String expectedAccessCode;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        loadArchiveCatalog();

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(20, 20, 20, 20);

        TextView heading = new TextView(this);
        heading.setText("DuckWebView — Archive Preview");
        heading.setTextSize(22);
        root.addView(heading);

        TextView description = new TextView(this);
        description.setText(
                "Preview archive HTML and inspect the available functionality."
        );
        root.addView(description);

        htmlInput = new EditText(this);
        htmlInput.setHint("Enter HTML preview content");
        htmlInput.setInputType(
                InputType.TYPE_CLASS_TEXT
                        | InputType.TYPE_TEXT_FLAG_MULTI_LINE
        );
        htmlInput.setMinLines(3);
        htmlInput.setText(
                "<h3>Archive preview</h3><p>Welcome.</p>"
        );

        root.addView(
                htmlInput,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                )
        );

        Button preview = new Button(this);
        preview.setText("Preview HTML");
        root.addView(preview);

        webView = new WebView(this);
        root.addView(
                webView,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        0,
                        1f
                )
        );

        setContentView(root);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);

        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());

        // Intentionally vulnerable for this isolated CTF.
        webView.addJavascriptInterface(
                new ArchiveBridge(),
                "DuckBridge"
        );

        preview.setOnClickListener(v -> {
            String html = htmlInput.getText().toString();

            webView.loadDataWithBaseURL(
                    "https://challenge.invalid/",
                    html,
                    "text/html",
                    "UTF-8",
                    null
            );
        });

        webView.loadDataWithBaseURL(
                "https://challenge.invalid/",
                "<h3>Archive preview</h3>"
                        + "<p>Enter HTML above and tap Preview HTML.</p>",
                "text/html",
                "UTF-8",
                null
        );
    }

    private void loadArchiveCatalog() {
        try (InputStream input =
                     getAssets().open("archive_catalog.json");
             BufferedReader reader = new BufferedReader(
                     new InputStreamReader(
                             input,
                             StandardCharsets.UTF_8
                     ))) {

            StringBuilder content = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null) {
                content.append(line);
            }

            JSONObject catalog =
                    new JSONObject(content.toString());

            expectedRecordId = decodeBase64(
                    catalog.getString("archive_ref_b64")
            );

            expectedAccessCode = decodeBase64(
                    catalog.getString("access_code_b64")
            );

        } catch (Exception e) {
            throw new IllegalStateException(
                    "Could not load the archive catalog",
                    e
            );
        }
    }

    private String decodeBase64(String value) {
        byte[] decoded = Base64.decode(
                value,
                Base64.DEFAULT
        );

        return new String(
                decoded,
                StandardCharsets.UTF_8
        );
    }

    private String readResponse(HttpURLConnection connection)
            throws Exception {

        int status = connection.getResponseCode();

        InputStream stream =
                status >= 200 && status < 400
                        ? connection.getInputStream()
                        : connection.getErrorStream();

        if (stream == null) {
            throw new IllegalStateException(
                    "Empty response from archive service"
            );
        }

        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(
                        stream,
                        StandardCharsets.UTF_8
                ))) {

            StringBuilder result = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null) {
                result.append(line);
            }

            return result.toString();
        }
    }

    private String requestJson(
            String path,
            JSONObject body
    ) throws Exception {

        HttpURLConnection connection = null;

        try {
            URL url = new URL(API_BASE + path);
            connection =
                    (HttpURLConnection) url.openConnection();

            connection.setConnectTimeout(5000);
            connection.setReadTimeout(5000);
            connection.setRequestProperty(
                    "Accept",
                    "application/json"
            );

            if (body == null) {
                connection.setRequestMethod("GET");
            } else {
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setRequestProperty(
                        "Content-Type",
                        "application/json; charset=UTF-8"
                );

                byte[] payload = body.toString()
                        .getBytes(StandardCharsets.UTF_8);

                try (OutputStream output =
                             connection.getOutputStream()) {
                    output.write(payload);
                }
            }

            return readResponse(connection);

        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    public final class ArchiveBridge {

        @JavascriptInterface
        public String getArchiveStatus() {
            return "Archive bridge online";
        }

        @JavascriptInterface
        public String openArchiveRecord(
                String recordId,
                String accessCode
        ) {
            if (expectedRecordId == null
                    || expectedAccessCode == null) {
                return errorJson("Archive catalog unavailable");
            }

            if (!expectedRecordId.equals(recordId)
                    || !expectedAccessCode.equals(accessCode)) {
                return errorJson(
                        "Invalid archive record or access code"
                );
            }

            try {
                // Obtain a short-lived, single-use server challenge.
                JSONObject challenge = new JSONObject(
                        requestJson(
                                "/api/archive/challenge",
                                null
                        )
                );

                String nonce = challenge.getString("nonce");

                JSONObject request = new JSONObject();
                request.put("record_id", recordId);
                request.put("access_code", accessCode);
                request.put("nonce", nonce);

                // The flag is returned by the server, not embedded
                // in this Android application.
                return requestJson(
                        "/api/archive/query",
                        request
                );

            } catch (Exception e) {
                return errorJson(
                        "Archive service unavailable: "
                                + e.getClass().getSimpleName()
                );
            }
        }

        private String errorJson(String message) {
            try {
                JSONObject response = new JSONObject();
                response.put("error", message);
                return response.toString();
            } catch (Exception e) {
                return "{\"error\":\"Request failed\"}";
            }
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.removeJavascriptInterface("DuckBridge");
            webView.destroy();
        }

        super.onDestroy();
    }
}
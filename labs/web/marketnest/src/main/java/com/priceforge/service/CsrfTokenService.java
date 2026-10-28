package com.priceforge.service;

import jakarta.servlet.http.HttpSession;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;

@Service
public class CsrfTokenService {

    private static final String SESSION_KEY = "priceforge_csrf";

    private final SecureRandom random = new SecureRandom();

    public String token(HttpSession session) {
        Object existing = session.getAttribute(SESSION_KEY);
        if (existing instanceof String value && !value.isBlank()) {
            return value;
        }
        String value = newToken();
        session.setAttribute(SESSION_KEY, value);
        return value;
    }

    public synchronized boolean consume(HttpSession session, String submitted) {
        if (session == null) {
            return false;
        }
        Object existing = session.getAttribute(SESSION_KEY);
        if (!(existing instanceof String expected) || submitted == null) {
            return false;
        }
        boolean valid = MessageDigest.isEqual(
                expected.getBytes(java.nio.charset.StandardCharsets.UTF_8),
                submitted.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        if (valid) {
            session.removeAttribute(SESSION_KEY);
        }
        return valid;
    }

    private String newToken() {
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}

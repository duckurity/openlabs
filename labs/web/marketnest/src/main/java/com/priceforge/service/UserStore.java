package com.priceforge.service;

import org.springframework.stereotype.Service;

import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

@Service
public class UserStore {

    private static final int ITERATIONS = 120_000;
    private static final int KEY_BITS = 256;
    private final SecureRandom secureRandom = new SecureRandom();
    private final Map<String, Credential> users = new ConcurrentHashMap<>();

    public boolean register(String username, String password) {
        if (username == null || !username.matches("[A-Za-z0-9_.-]{3,32}")
                || password == null || password.length() < 8) {
            return false;
        }

        byte[] salt = new byte[16];
        secureRandom.nextBytes(salt);
        return users.putIfAbsent(username, new Credential(salt, derive(password, salt))) == null;
    }

    public boolean isValid(String username, String password) {
        Credential credential = users.get(username);
        if (credential == null || password == null) {
            return false;
        }
        return MessageDigest.isEqual(credential.hash(), derive(password, credential.salt()));
    }

    private byte[] derive(String password, byte[] salt) {
        try {
            PBEKeySpec spec = new PBEKeySpec(password.toCharArray(), salt, ITERATIONS, KEY_BITS);
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
                    .generateSecret(spec).getEncoded();
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("Unable to derive password hash", e);
        }
    }

    private record Credential(byte[] salt, byte[] hash) {
        private Credential {
            salt = Arrays.copyOf(salt, salt.length);
            hash = Arrays.copyOf(hash, hash.length);
        }
    }
}

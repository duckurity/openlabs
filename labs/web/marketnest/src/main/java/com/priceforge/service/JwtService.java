package com.priceforge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Service;

import java.math.BigInteger;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.Signature;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.RSAPublicKeySpec;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class JwtService {

    private static final String KEY_ID = "marketnest-main-key";
    private static final String ISSUER = "marketnest";
    private static final long TOKEN_LIFETIME_SECONDS = 3600;

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3))
            .build();
    private KeyPair serverKeyPair;

    public JwtService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void initializeKeys() {
        try {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
            generator.initialize(2048);
            serverKeyPair = generator.generateKeyPair();
        } catch (Exception e) {
            throw new IllegalStateException("Unable to initialize JWT keys", e);
        }
    }

    /**
     * Issue the ordinary application token. It deliberately does not include
     * a jku header; the vulnerable verifier still accepts one if a player
     * adds it to a forged token.
     */
    public String issue(String username) {
        return issue(username, null);
    }

    private String issue(String username, String jku) {
        long now = Instant.now().getEpochSecond();

        Map<String, Object> header = new LinkedHashMap<>();
        header.put("alg", "RS256");
        header.put("typ", "JWT");
        header.put("kid", KEY_ID);
        if (jku != null && !jku.isBlank()) {
            header.put("jku", jku);
        }

        Map<String, Object> claims = new LinkedHashMap<>();
        claims.put("iss", ISSUER);
        claims.put("sub", username);
        claims.put("role", "retailer");
        claims.put("iat", now);
        claims.put("exp", now + TOKEN_LIFETIME_SECONDS);

        try {
            String encodedHeader = encodeJson(header);
            String encodedClaims = encodeJson(claims);
            String signingInput = encodedHeader + "." + encodedClaims;
            Signature signature = Signature.getInstance("SHA256withRSA");
            signature.initSign(serverKeyPair.getPrivate());
            signature.update(signingInput.getBytes(StandardCharsets.UTF_8));
            return signingInput + "." + encode(signature.sign());
        } catch (Exception e) {
            throw new IllegalStateException("Unable to issue JWT", e);
        }
    }

    /**
     * Deliberately vulnerable for the CTF: the untrusted jku header controls
     * where the verification key is fetched from. There is no host allowlist.
     */
    public JwtIdentity verify(String token) throws Exception {
        String[] parts = token.split("\\.");
        if (parts.length != 3) {
            throw new SecurityException("Malformed JWT");
        }

        JsonNode header = objectMapper.readTree(new String(decode(parts[0]), StandardCharsets.UTF_8));
        JsonNode claims = objectMapper.readTree(new String(decode(parts[1]), StandardCharsets.UTF_8));
        if (!"RS256".equals(header.path("alg").asText())) {
            throw new SecurityException("Unsupported JWT algorithm");
        }

        String kid = header.path("kid").asText();
        String jku = header.path("jku").asText();
        java.security.PublicKey verificationKey = jku.isBlank()
                ? serverKeyPair.getPublic()
                : fetchKey(jku, kid);

        Signature signature = Signature.getInstance("SHA256withRSA");
        signature.initVerify(verificationKey);
        signature.update((parts[0] + "." + parts[1]).getBytes(StandardCharsets.UTF_8));
        if (!signature.verify(decode(parts[2]))) {
            throw new SecurityException("Invalid JWT signature");
        }

        if (!ISSUER.equals(claims.path("iss").asText())
                || claims.path("exp").asLong(0) < Instant.now().getEpochSecond()) {
            throw new SecurityException("Expired or invalid JWT claims");
        }

        return new JwtIdentity(claims.path("sub").asText(), claims.path("role").asText());
    }

    public Map<String, Object> publicJwkSet() {
        RSAPublicKey publicKey = (RSAPublicKey) serverKeyPair.getPublic();
        Map<String, Object> key = new LinkedHashMap<>();
        key.put("kty", "RSA");
        key.put("use", "sig");
        key.put("alg", "RS256");
        key.put("kid", KEY_ID);
        key.put("n", encodeUnsigned(publicKey.getModulus()));
        key.put("e", encodeUnsigned(publicKey.getPublicExponent()));
        Map<String, Object> jwks = new LinkedHashMap<>();
        jwks.put("keys", List.of(key));
        return jwks;
    }

    private java.security.PublicKey fetchKey(String jku, String kid) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create(jku))
                .timeout(Duration.ofSeconds(5))
                .header("Accept", "application/json")
                .GET()
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() != 200) {
            throw new SecurityException("Unable to fetch JWKS");
        }

        JsonNode keys = objectMapper.readTree(response.body()).path("keys");
        for (JsonNode key : keys) {
            if (kid.equals(key.path("kid").asText()) && "RSA".equals(key.path("kty").asText())) {
                byte[] modulus = decode(key.path("n").asText());
                byte[] exponent = decode(key.path("e").asText());
                RSAPublicKeySpec spec = new RSAPublicKeySpec(
                        new BigInteger(1, modulus), new BigInteger(1, exponent));
                return KeyFactory.getInstance("RSA").generatePublic(spec);
            }
        }
        throw new SecurityException("No matching JWK");
    }

    private String encodeJson(Object value) throws Exception {
        return encode(objectMapper.writeValueAsBytes(value));
    }

    private String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private String encodeUnsigned(BigInteger value) {
        byte[] bytes = value.toByteArray();
        if (bytes.length > 1 && bytes[0] == 0) {
            bytes = Arrays.copyOfRange(bytes, 1, bytes.length);
        }
        return encode(bytes);
    }

    private byte[] decode(String value) {
        return Base64.getUrlDecoder().decode(value);
    }

    public record JwtIdentity(String subject, String role) {
    }
}

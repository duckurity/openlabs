package com.priceforge.web;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import com.priceforge.service.JwtService;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Component
public class SessionFilter implements Filter {

    private final JwtService jwtService;

    public SessionFilter(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) req;
        HttpServletResponse response = (HttpServletResponse) res;
        String path = request.getRequestURI();

        boolean protectedPath = path.startsWith("/dashboard")
                || path.startsWith("/import")
                || path.startsWith("/catalog")
                || path.startsWith("/orders");

        if (protectedPath) {
            String token = getToken(request);
            if (token == null) {
                response.sendRedirect("/login");
                return;
            }

            JwtService.JwtIdentity identity;
            try {
                identity = jwtService.verify(token);
            } catch (Exception e) {
                response.sendRedirect("/login");
                return;
            }

            request.setAttribute("jwtIdentity", identity);
            if (path.startsWith("/import") && !"admin".equalsIgnoreCase(identity.role())) {
                response.sendRedirect("/dashboard");
                return;
            }
        }

        chain.doFilter(req, res);
    }

    private String getToken(HttpServletRequest request) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return null;
        }

        for (Cookie cookie : cookies) {
            if ("pf_token".equals(cookie.getName())) {
                return cookie.getValue();
            }
        }
        return null;
    }
}

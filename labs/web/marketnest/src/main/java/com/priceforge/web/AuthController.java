package com.priceforge.web;

import java.io.IOException;
import com.priceforge.service.UserStore;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import com.priceforge.service.JwtService;
import com.priceforge.service.CsrfTokenService;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
public class AuthController {

    private final UserStore userStore;
    private final JwtService jwtService;
    private final CsrfTokenService csrfTokenService;
    public AuthController(UserStore userStore,
                          JwtService jwtService,
                          CsrfTokenService csrfTokenService) {
        this.userStore = userStore;
        this.jwtService = jwtService;
        this.csrfTokenService = csrfTokenService;
    }

    @GetMapping("/login")
    public String loginForm(HttpServletRequest request, Model model) {
        model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
        return "login";
    }

    @GetMapping("/signup")
    public String signupForm(HttpServletRequest request, Model model) {
        model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
        return "signup";
    }

    @PostMapping("/signup")
    public String signup(@RequestParam String username,
                         @RequestParam String password,
                         @RequestParam(name = "_csrf", defaultValue = "") String csrfToken,
                         HttpServletRequest request,
                         Model model) {
        if (!csrfTokenService.consume(request.getSession(false), csrfToken)) {
            model.addAttribute("error", "Your form has expired. Please try again.");
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            return "signup";
        }
        if (userStore.register(username, password)) {
            return "redirect:/login?registered=true";
        }
        model.addAttribute("error", "Username is taken or input is invalid");
        return "signup";
    }

    @PostMapping("/login")
    public String login(@RequestParam String username,
                         @RequestParam String password,
                         @RequestParam(name = "_csrf", defaultValue = "") String csrfToken,
        HttpServletRequest request,
        HttpServletResponse response,
        Model model) {
        if (!csrfTokenService.consume(request.getSession(false), csrfToken)) {
            model.addAttribute("error", "Your form has expired. Please try again.");
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            return "login";
        }
        if (userStore.isValid(username, password)) {
            ResponseCookie tokenCookie = ResponseCookie.from("pf_token", jwtService.issue(username))
                    .httpOnly(true)
                    .secure(request.isSecure())
                    .sameSite("Lax")
                    .path("/")
                    .maxAge(3600)
                    .build();
            response.addHeader(HttpHeaders.SET_COOKIE, tokenCookie.toString());
            return "redirect:/dashboard";
        }
        model.addAttribute("error", "Invalid username or password");
        return "login";
    }

    @PostMapping("/logout")
    public String logout(@RequestParam(name = "_csrf", defaultValue = "") String csrfToken,
                         HttpServletRequest request,
                         HttpServletResponse response) throws IOException {
        if (!csrfTokenService.consume(request.getSession(false), csrfToken)) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN);
            return null;
        }
        ResponseCookie tokenCookie = ResponseCookie.from("pf_token", "")
                .httpOnly(true)
                .secure(request.isSecure())
                .sameSite("Lax")
                .path("/")
                .maxAge(0)
                .build();
        response.addHeader(HttpHeaders.SET_COOKIE, tokenCookie.toString());
        return "redirect:/login";
    }
}

package com.priceforge.web;

import com.priceforge.service.CsrfTokenService;
import com.priceforge.service.JwtService;
import com.priceforge.service.WorkspaceService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
public class OperationsController {

    private final WorkspaceService workspaceService;
    private final CsrfTokenService csrfTokenService;

    public OperationsController(WorkspaceService workspaceService, CsrfTokenService csrfTokenService) {
        this.workspaceService = workspaceService;
        this.csrfTokenService = csrfTokenService;
    }

    @GetMapping("/catalog")
    public String catalog(HttpServletRequest request, Model model) {
        String username = addIdentity(request, model);
        model.addAttribute("catalog", workspaceService.getCatalog(username));
        return "catalog";
    }

    @GetMapping("/orders")
    public String orders(HttpServletRequest request, Model model) {
        String username = addIdentity(request, model);
        var orders = workspaceService.getOrders(username);
        model.addAttribute("orders", orders);
        model.addAttribute("orderRevenue", String.format("$%,.2f", workspaceService.getOrderRevenue(username)));
        model.addAttribute("averageOrder", String.format("$%,.2f", workspaceService.getOrderRevenue(username) / orders.size()));
        return "orders";
    }

    @GetMapping("/orders/new")
    public String newOrder(HttpServletRequest request, Model model) {
        String username = addIdentity(request, model);
        model.addAttribute("catalog", workspaceService.getCatalog(username));
        model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
        return "new-order";
    }

    @PostMapping("/orders")
    public String createOrder(@RequestParam(defaultValue = "") String customer,
                              @RequestParam(defaultValue = "") String sku,
                              @RequestParam(name = "quantity", defaultValue = "") String quantityValue,
                              @RequestParam(name = "_csrf", defaultValue = "") String csrfToken,
                              HttpServletRequest request,
                              Model model) {
        String username = addIdentity(request, model);
        HttpSession session = request.getSession(false);
        if (session == null || !csrfTokenService.consume(session, csrfToken)) {
            model.addAttribute("error", "Your form has expired. Please open a fresh order form.");
            model.addAttribute("catalog", workspaceService.getCatalog(username));
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            return "new-order";
        }

        if (customer == null || !customer.matches("[A-Za-z0-9][A-Za-z0-9 .&'\\-]{1,79}")) {
            model.addAttribute("error", "Enter a valid customer name using letters, numbers, spaces, or punctuation.");
            model.addAttribute("catalog", workspaceService.getCatalog(username));
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            return "new-order";
        }

        int quantity;
        try {
            quantity = Integer.parseInt(quantityValue);
        } catch (NumberFormatException exception) {
            quantity = 0;
        }
        if (quantity < 1 || quantity > 999) {
            model.addAttribute("error", "Quantity must be between 1 and 999.");
            model.addAttribute("catalog", workspaceService.getCatalog(username));
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            return "new-order";
        }

        try {
            workspaceService.createOrder(username, customer.trim(), sku, quantity);
            return "redirect:/orders?created=true";
        } catch (IllegalArgumentException exception) {
            model.addAttribute("error", exception.getMessage());
            model.addAttribute("catalog", workspaceService.getCatalog(username));
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            return "new-order";
        }
    }

    private String addIdentity(HttpServletRequest request, Model model) {
        Object identity = request.getAttribute("jwtIdentity");
        if (identity instanceof JwtService.JwtIdentity jwtIdentity) {
            model.addAttribute("username", jwtIdentity.subject());
            model.addAttribute("isAdmin", "admin".equalsIgnoreCase(jwtIdentity.role()));
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            return jwtIdentity.subject();
        }
        throw new IllegalStateException("Authenticated workspace identity missing");
    }
}

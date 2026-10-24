package com.priceforge.web;

import jakarta.servlet.http.HttpServletRequest;
import com.priceforge.service.WorkspaceService;
import com.priceforge.service.CsrfTokenService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class DashboardController {

    private final WorkspaceService workspaceService;
    private final CsrfTokenService csrfTokenService;

    public DashboardController(WorkspaceService workspaceService, CsrfTokenService csrfTokenService) {
        this.workspaceService = workspaceService;
        this.csrfTokenService = csrfTokenService;
    }

    @GetMapping("/dashboard")
    public String dashboard(HttpServletRequest request, Model model) {
        Object identity = request.getAttribute("jwtIdentity");
        if (identity instanceof com.priceforge.service.JwtService.JwtIdentity jwtIdentity) {
            model.addAttribute("username", jwtIdentity.subject());
            model.addAttribute("isAdmin", "admin".equalsIgnoreCase(jwtIdentity.role()));
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            model.addAttribute("productCount", workspaceService.getProductCount(jwtIdentity.subject()));
            model.addAttribute("inventoryValue", String.format("$%,.2f", workspaceService.getInventoryValue(jwtIdentity.subject())));
            model.addAttribute("lowStockCount", workspaceService.getLowStockCount(jwtIdentity.subject()));
            model.addAttribute("orderCount", workspaceService.getOrders(jwtIdentity.subject()).size());
            model.addAttribute("orderRevenue", String.format("$%,.2f", workspaceService.getOrderRevenue(jwtIdentity.subject())));
            var catalog = workspaceService.getCatalog(jwtIdentity.subject());
            var orders = workspaceService.getOrders(jwtIdentity.subject());
            model.addAttribute("catalogPreview", catalog.subList(0, Math.min(4, catalog.size())));
            model.addAttribute("recentOrders", orders.subList(0, Math.min(3, orders.size())));
        }
        return "dashboard";
    }
}

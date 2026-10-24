package com.priceforge.service;

import com.priceforge.model.CatalogItem;
import com.priceforge.model.OrderSummary;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class WorkspaceService {

    private final Map<String, UserWorkspace> workspaces = new ConcurrentHashMap<>();
    private final SecureRandom random = new SecureRandom();

    public List<CatalogItem> getCatalog(String username) {
        return workspace(username).catalog;
    }

    public List<OrderSummary> getOrders(String username) {
        return List.copyOf(workspace(username).orders);
    }

    public int getProductCount(String username) {
        return workspace(username).catalog.size();
    }

    public double getInventoryValue(String username) {
        return workspace(username).catalog.stream()
                .mapToDouble(item -> item.getPrice() * item.getStock())
                .sum();
    }

    public long getLowStockCount(String username) {
        return workspace(username).catalog.stream()
                .filter(item -> item.getStock() < 20)
                .count();
    }

    public double getOrderRevenue(String username) {
        return workspace(username).orders.stream()
                .mapToDouble(OrderSummary::getTotal)
                .sum();
    }

    public synchronized String createOrder(String username, String customer, String sku, int quantity) {
        UserWorkspace userWorkspace = workspace(username);
        CatalogItem item = userWorkspace.catalog.stream()
                .filter(candidate -> candidate.getSku().equals(sku))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Choose a product from the catalog"));

        if (!item.reserve(quantity)) {
            throw new IllegalArgumentException("Requested quantity is not available");
        }

        double total = item.getPrice() * quantity;
        String orderNumber = newOrderNumber();
        userWorkspace.orders.add(0, new OrderSummary(orderNumber, customer,
                item.getName() + " x " + quantity, "Processing", total, "Just now"));
        return orderNumber;
    }

    private UserWorkspace workspace(String username) {
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("A workspace identity is required");
        }
        return workspaces.computeIfAbsent(username, ignored -> new UserWorkspace());
    }

    private String newOrderNumber() {
        byte[] bytes = new byte[4];
        random.nextBytes(bytes);
        StringBuilder value = new StringBuilder("#PF-");
        for (byte byteValue : bytes) {
            value.append(String.format(Locale.ROOT, "%02X", byteValue));
        }
        return value.toString();
    }

    private static class UserWorkspace {
        private final List<CatalogItem> catalog = new CopyOnWriteArrayList<>(seedCatalog());
        private final List<OrderSummary> orders = new CopyOnWriteArrayList<>(seedOrders());

        private static List<CatalogItem> seedCatalog() {
            return new ArrayList<>(List.of(
                    new CatalogItem("BRW-1042", "House Blend Coffee", "Beverages", 14.50, 86),
                    new CatalogItem("PAN-2081", "Sourdough Loaf", "Bakery", 6.75, 18),
                    new CatalogItem("OLV-3307", "Castelvetrano Olives", "Pantry", 9.25, 42),
                    new CatalogItem("MUG-4410", "Stoneware Mug", "Home goods", 18.00, 64),
                    new CatalogItem("HNY-5122", "Wildflower Honey", "Pantry", 12.00, 27),
                    new CatalogItem("TOW-6903", "Linen Kitchen Towel", "Home goods", 11.50, 9)
            ));
        }

        private static List<OrderSummary> seedOrders() {
            return new ArrayList<>(List.of(
                    new OrderSummary("#PF-2048", "Maya's Market", "6 products", "Processing", 86.25, "Today, 09:42"),
                    new OrderSummary("#PF-2047", "Northside Pantry", "9 products", "Ready to ship", 142.80, "Yesterday, 16:18"),
                    new OrderSummary("#PF-2046", "The Corner Table", "3 products", "Completed", 54.50, "Yesterday, 11:03"),
                    new OrderSummary("#PF-2045", "Harbor & Grain", "14 products", "Completed", 219.10, "Mon, 14:27")
            ));
        }
    }
}

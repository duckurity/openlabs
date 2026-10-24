package com.priceforge.model;

public class OrderSummary {

    private final String orderNumber;
    private final String customer;
    private final String items;
    private final String status;
    private final double total;
    private final String placedAt;

    public OrderSummary(String orderNumber, String customer, String items, String status, double total, String placedAt) {
        this.orderNumber = orderNumber;
        this.customer = customer;
        this.items = items;
        this.status = status;
        this.total = total;
        this.placedAt = placedAt;
    }

    public String getOrderNumber() { return orderNumber; }
    public String getCustomer() { return customer; }
    public String getItems() { return items; }
    public String getStatus() { return status; }
    public double getTotal() { return total; }
    public String getPlacedAt() { return placedAt; }
}

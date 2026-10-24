package com.priceforge.model;

public class CatalogItem {

    private final String sku;
    private final String name;
    private final String category;
    private final double price;
    private int stock;

    public CatalogItem(String sku, String name, String category, double price, int stock) {
        this.sku = sku;
        this.name = name;
        this.category = category;
        this.price = price;
        this.stock = stock;
    }

    public String getSku() { return sku; }
    public String getName() { return name; }
    public String getCategory() { return category; }
    public double getPrice() { return price; }
    public int getStock() { return stock; }

    public synchronized boolean reserve(int quantity) {
        if (quantity < 1 || quantity > stock) {
            return false;
        }
        stock -= quantity;
        return true;
    }

    public String getStockLabel() {
        if (stock < 20) return "Low stock";
        if (stock < 50) return "Watch stock";
        return "In stock";
    }
}

package com.priceforge.model;

/**
 * Minimal product record. This is set as the SpEL root object during
 * formula evaluation, which is why a formula can reference "basePrice"
 * directly (it resolves via getBasePrice()).
 */
public class Product {

    private String name;
    private double basePrice;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public double getBasePrice() {
        return basePrice;
    }

    public void setBasePrice(double basePrice) {
        this.basePrice = basePrice;
    }
}

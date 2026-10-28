package com.priceforge.model;

/**
 * One row of the import preview. "computedValue" is whatever the pricing
 * formula evaluates to, rendered via toString() - this is intentionally
 * the ONLY feedback channel the import process exposes back to the user.
 */
public class ImportResult {

    private String name;
    private double basePrice;
    private String formula;
    private String computedValue;

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

    public String getFormula() {
        return formula;
    }

    public void setFormula(String formula) {
        this.formula = formula;
    }

    public String getComputedValue() {
        return computedValue;
    }

    public void setComputedValue(String computedValue) {
        this.computedValue = computedValue;
    }
}

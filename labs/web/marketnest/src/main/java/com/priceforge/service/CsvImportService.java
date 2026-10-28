package com.priceforge.service;

import com.priceforge.model.ImportResult;
import com.priceforge.model.Product;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

@Service
public class CsvImportService {

    private final PricingService pricingService;

    public CsvImportService(PricingService pricingService) {
        this.pricingService = pricingService;
    }

    /**
     * Expected columns: name,basePrice,stock,priceFormula
     * (stock is accepted but not used in this minimal demo app)
     */
    public List<ImportResult> processFile(MultipartFile file) throws IOException {
        List<ImportResult> results = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {

            String header = reader.readLine(); // skip header row
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }

                ImportResult result = new ImportResult();

                try {
                    List<String> fields = parseCsvLine(line);
                    if (fields.size() < 4) {
                        result.setComputedValue("ERROR: expected 4 columns, got " + fields.size());
                        results.add(result);
                        continue;
                    }

                    String name = fields.get(0).trim();
                    double basePrice = Double.parseDouble(fields.get(1).trim());
                    String formula = fields.get(3).trim();

                    result.setName(name);
                    result.setBasePrice(basePrice);
                    result.setFormula(formula);

                    Product product = new Product();
                    product.setName(name);
                    product.setBasePrice(basePrice);

                    Object computed = pricingService.evaluate(formula, product);
                    result.setComputedValue(String.valueOf(computed));

                } catch (SecurityException e) {
                    // Keep the deliberate blacklist signal visible to players.
                    result.setComputedValue("ERROR: " + e.getMessage());
                } catch (Exception e) {
                    // Do not expose raw Spring/Java implementation details.
                    result.setComputedValue("ERROR: Formula evaluation failed. Check the expression syntax.");
                }

                results.add(result);
            }
        }

        return results;
    }

    private List<String> parseCsvLine(String line) {
        List<String> fields = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean inQuotes = false;

        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') {
                if (inQuotes && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    current.append('"');
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (c == ',' && !inQuotes) {
                fields.add(current.toString());
                current.setLength(0);
            } else {
                current.append(c);
            }
        }
        fields.add(current.toString());
        return fields;
    }
}

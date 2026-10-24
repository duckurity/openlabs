package com.priceforge.web;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class HomeController {

    @GetMapping("/")
    public String home() {
        return "redirect:/login";
    }

    @GetMapping("/static/templates/bulk_import_sample.csv")
    public String sampleCsv() {
        return "redirect:/templates/bulk_import_sample.csv";
    }
}

package com.priceforge.web;

import com.priceforge.model.ImportResult;
import com.priceforge.service.CsvImportService;
import com.priceforge.service.CsrfTokenService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;
import jakarta.servlet.http.HttpServletRequest;

import java.io.IOException;
import java.util.List;

@Controller
public class ImportController {

    private final CsvImportService csvImportService;
    private final CsrfTokenService csrfTokenService;

    public ImportController(CsvImportService csvImportService, CsrfTokenService csrfTokenService) {
        this.csvImportService = csvImportService;
        this.csrfTokenService = csrfTokenService;
    }

    @GetMapping("/import")
    public String importForm(HttpServletRequest request, Model model) {
        addUsername(request, model);
        model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
        return "import";
    }

    @PostMapping("/import")
    public String handleImport(@RequestParam("file") MultipartFile file,
                               @RequestParam(name = "_csrf", defaultValue = "") String csrfToken,
                               HttpServletRequest request,
                               Model model) throws IOException {
        if (!csrfTokenService.consume(request.getSession(false), csrfToken)) {
            addUsername(request, model);
            model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
            model.addAttribute("error", "Your form has expired. Please open a fresh import form.");
            return "import";
        }
        List<ImportResult> results = csvImportService.processFile(file);
        model.addAttribute("results", results);
        addUsername(request, model);
        model.addAttribute("csrfToken", csrfTokenService.token(request.getSession(true)));
        return "result";
    }

    private void addUsername(HttpServletRequest request, Model model) {
        Object identity = request.getAttribute("jwtIdentity");
        if (identity instanceof com.priceforge.service.JwtService.JwtIdentity jwtIdentity) {
            model.addAttribute("username", jwtIdentity.subject());
        }
    }
}

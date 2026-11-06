using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using VaultCorp.Services;

namespace VaultCorp.Pages.Admin;

public class ImportModel : PageModel
{
    private readonly UrlFetchService _fetcher;

    public FetchResult? Result  { get; private set; }
    public string       LastUrl { get; private set; } = string.Empty;

    public ImportModel(UrlFetchService fetcher) => _fetcher = fetcher;

    public IActionResult OnGet()
    {
        if (HttpContext.Session.GetString("Role") != "Admin")
            return RedirectToPage("/Login");
        return Page();
    }

    public async Task<IActionResult> OnPostAsync(string url)
    {
        if (HttpContext.Session.GetString("Role") != "Admin")
            return RedirectToPage("/Login");

        LastUrl = url;
        Result  = await _fetcher.FetchAsync(url);
        return Page();
    }
}

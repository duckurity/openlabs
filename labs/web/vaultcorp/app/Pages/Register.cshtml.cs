using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using VaultCorp.Data;
using VaultCorp.Services;

namespace VaultCorp.Pages;

public class RegisterModel : PageModel
{
    private readonly TenantService _tenants;
    private readonly AppDbContext  _db;

    public string Error { get; private set; } = string.Empty;

    public RegisterModel(TenantService tenants, AppDbContext db)
    {
        _tenants = tenants;
        _db      = db;
    }

    public IActionResult OnGet()
    {
        if (HttpContext.Session.GetString("UserId") != null)
            return RedirectToPage("/Dashboard");
        return Page();
    }

    public async Task<IActionResult> OnPostAsync(string username, string password)
    {
        if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(password))
        {
            Error = "Username and password are required.";
            return Page();
        }

        // Check username uniqueness (across all tenants)
        if (_db.Users.Any(u => u.Username == username))
        {
            Error = "Username already taken.";
            return Page();
        }

        var (_, player) = await _tenants.ProvisionAsync(username, password);

        HttpContext.Session.SetString("UserId",   player.Id.ToString());
        HttpContext.Session.SetString("TenantId", player.TenantId);
        HttpContext.Session.SetString("Role",     player.Role);
        HttpContext.Session.SetString("Username", player.Username);

        return RedirectToPage("/Dashboard");
    }
}

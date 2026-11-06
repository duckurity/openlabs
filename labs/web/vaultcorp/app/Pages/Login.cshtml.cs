using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using VaultCorp.Data;

namespace VaultCorp.Pages;

public class LoginModel : PageModel
{
    private readonly AppDbContext _db;
    public string Error { get; private set; } = string.Empty;

    public LoginModel(AppDbContext db) => _db = db;

    public IActionResult OnGet()
    {
        if (HttpContext.Session.GetString("UserId") != null)
            return RedirectToPage("/Dashboard");
        return Page();
    }

    public IActionResult OnPost(string username, string password)
    {
        var user = _db.Users.FirstOrDefault(u => u.Username == username && !u.IsNoise);
        if (user is null || !BCrypt.Net.BCrypt.Verify(password, user.PasswordHash))
        {
            Error = "Invalid credentials.";
            return Page();
        }

        HttpContext.Session.SetString("UserId",   user.Id.ToString());
        HttpContext.Session.SetString("TenantId", user.TenantId);
        HttpContext.Session.SetString("Role",     user.Role);
        HttpContext.Session.SetString("Username", user.Username);

        return user.Role == "Admin"
            ? RedirectToPage("/Admin/Index")
            : RedirectToPage("/Dashboard");
    }
}

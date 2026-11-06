using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using VaultCorp.Data;

namespace VaultCorp.Pages;

public class SupportLoginModel : PageModel
{
    private readonly AppDbContext _db;
    public string Error { get; private set; } = string.Empty;

    public SupportLoginModel(AppDbContext db) => _db = db;

    public void OnGet() { }

    public IActionResult OnPost(string refId, string token)
    {
        if (!int.TryParse(refId, out int localId))
        {
            Error = "Invalid support credentials.";
            return Page();
        }

        // Find admin whose LocalId and ApiToken match — tenant-agnostic (support staff
        // are supposed to access any org, but in practice the fixtures only expose
        // the admin of the current player's tenant).
        // Fixtures encode the token as "tk_{ApiToken}" — strip prefix before lookup
        var cleanToken = token.StartsWith("tk_") ? token[3..] : token;

        var admin = _db.Users.FirstOrDefault(u =>
            u.LocalId  == localId     &&
            u.ApiToken == cleanToken  &&
            u.Role     == "Admin");

        if (admin is null)
        {
            Error = "Invalid support credentials.";
            return Page();
        }

        HttpContext.Session.SetString("UserId",   admin.Id.ToString());
        HttpContext.Session.SetString("TenantId", admin.TenantId);
        HttpContext.Session.SetString("Role",     admin.Role);
        HttpContext.Session.SetString("Username", admin.Username);

        return RedirectToPage("/Admin/Index");
    }
}

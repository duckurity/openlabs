using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using VaultCorp.Data;

namespace VaultCorp.Pages;

public class DashboardModel : PageModel
{
    private readonly AppDbContext _db;

    public string CompanyName { get; private set; } = string.Empty;
    public int    BackupCount { get; private set; }
    public int    TeamSize    { get; private set; }

    public DashboardModel(AppDbContext db) => _db = db;

    public IActionResult OnGet()
    {
        var tenantId = HttpContext.Session.GetString("TenantId");
        if (tenantId is null) return RedirectToPage("/Login");

        var tenant = _db.Tenants.Find(tenantId);
        CompanyName = tenant?.CompanyName ?? "Your Organisation";
        TeamSize    = _db.Users.Count(u => u.TenantId == tenantId && !u.IsNoise);
        BackupCount = new Random().Next(4, 30); // cosmetic
        return Page();
    }
}

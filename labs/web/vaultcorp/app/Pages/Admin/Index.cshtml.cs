using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using VaultCorp.Data;
using VaultCorp.Data.Models;

namespace VaultCorp.Pages.Admin;

public class AdminIndexModel : PageModel
{
    private readonly AppDbContext _db;

    public List<User> Users       { get; private set; } = new();
    public int        UserCount   { get; private set; }
    public string     StorageUsed { get; private set; } = "0 MB";

    public AdminIndexModel(AppDbContext db) => _db = db;

    public IActionResult OnGet()
    {
        if (HttpContext.Session.GetString("Role") != "Admin")
            return RedirectToPage("/Login");

        var tenantId = HttpContext.Session.GetString("TenantId")!;
        Users       = _db.Users.Where(u => u.TenantId == tenantId).ToList();
        UserCount   = Users.Count;
        StorageUsed = $"{new Random().Next(10, 500)} MB";
        return Page();
    }
}

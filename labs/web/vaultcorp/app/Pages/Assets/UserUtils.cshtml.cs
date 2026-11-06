using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using VaultCorp.Data;

namespace VaultCorp.Pages.Assets;

public class UserUtilsModel : PageModel
{
    private readonly AppDbContext _db;

    public string T1 { get; private set; } = string.Empty;
    public string V1 { get; private set; } = string.Empty;
    public string T2 { get; private set; } = string.Empty;
    public string V2 { get; private set; } = string.Empty;
    public string T3 { get; private set; } = string.Empty;
    public string V3 { get; private set; } = string.Empty;

    public UserUtilsModel(AppDbContext db) => _db = db;

    public void OnGet()
    {
        Response.ContentType = "application/javascript; charset=utf-8";

        var tenantId = HttpContext.Session.GetString("TenantId");
        if (string.IsNullOrEmpty(tenantId)) return;

        var admin = _db.Users.FirstOrDefault(u =>
            u.TenantId == tenantId && u.Role == "Admin");

        // XOR key: 0x42
        static string Enc(string plain)
        {
            var bytes = System.Text.Encoding.UTF8.GetBytes(plain);
            for (int i = 0; i < bytes.Length; i++) bytes[i] ^= 0x42;
            return Convert.ToBase64String(bytes);
        }

        static string RandEnc()
        {
            var buf = new byte[20];
            Random.Shared.NextBytes(buf);
            for (int i = 0; i < buf.Length; i++) buf[i] ^= 0x42;
            return Convert.ToBase64String(buf);
        }

        var prodEnc = admin is null
            ? RandEnc()
            : Enc($"{admin.LocalId}:tk_{admin.ApiToken}");

        // Shuffle so prod is not always in same position
        var entries = new[]
        {
            ("stg-01", RandEnc()),
            ("prod",   prodEnc),
            ("stg-02", RandEnc())
        }.OrderBy(_ => Random.Shared.Next()).ToArray();

        (T1, V1) = entries[0];
        (T2, V2) = entries[1];
        (T3, V3) = entries[2];
    }
}

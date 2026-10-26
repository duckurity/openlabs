using VaultCorp.Data;
using VaultCorp.Data.Models;

namespace VaultCorp.Services;

public class TenantService
{
    private readonly AppDbContext _db;

    private static readonly string[] FakeFirstNames =
        { "Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank", "Iris", "Jack" };
    private static readonly string[] FakeLastNames =
        { "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson" };
    private static readonly string[] CompanyNames =
        { "Nexabit", "CoreSync", "DataVault", "CloudPeak", "ByteStream", "InfoSafe", "PrimeLock" };

    public TenantService(AppDbContext db) => _db = db;

    // ─── Called when a new user registers ───────────────────────────────────
    public async Task<(Tenant tenant, User player)> ProvisionAsync(
        string username, string password)
    {
        var rng   = new Random();
        var tenantId = Guid.NewGuid().ToString();

        // 1. Tenant record
        var tenant = new Tenant
        {
            Id          = tenantId,
            CompanyName = CompanyNames[rng.Next(CompanyNames.Length)] + " Inc.",
            CreatedAt   = DateTime.UtcNow
        };
        _db.Tenants.Add(tenant);

        // 2. Assign random LocalIds within 1–100 (no collision)
        var usedIds  = new HashSet<int>();
        int NextId() {
            int id;
            do { id = rng.Next(1, 101); } while (!usedIds.Add(id));
            return id;
        }

        // 3. Player account
        var player = new User
        {
            TenantId     = tenantId,
            LocalId      = NextId(),
            Username     = username,
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(password),
            Email        = $"{username.ToLower()}@{tenant.CompanyName.Replace(" ", "").ToLower()}.local",
            Role         = "Employee",
            ApiToken     = GenerateToken(),
            DisplayName  = username,
            IsNoise      = false
        };
        _db.Users.Add(player);

        // 4. Noise accounts (4–6 fake employees)
        int noiseCount = rng.Next(4, 7);
        for (int i = 0; i < noiseCount; i++)
        {
            var fn   = FakeFirstNames[rng.Next(FakeFirstNames.Length)];
            var ln   = FakeLastNames[rng.Next(FakeLastNames.Length)];
            var name = $"{fn}{ln}{rng.Next(10, 99)}";
            _db.Users.Add(new User
            {
                TenantId     = tenantId,
                LocalId      = NextId(),
                Username     = name,
                PasswordHash = BCrypt.Net.BCrypt.HashPassword(GenerateToken()),
                Email        = $"{name.ToLower()}@{tenant.CompanyName.Replace(" ", "").ToLower()}.local",
                Role         = "Employee",
                ApiToken     = GenerateToken(),
                DisplayName  = $"{fn} {ln}",
                IsNoise      = true
            });
        }

        // 5. Admin account (unique token — this is what leaks in the JS fixtures)
        var adminName = "svc_support_" + GenerateToken(6);
        var admin = new User
        {
            TenantId     = tenantId,
            LocalId      = NextId(),
            Username     = adminName,
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(GenerateToken(20)),
            Email        = $"{adminName}@vaultcorp-internal.io",
            Role         = "Admin",
            ApiToken     = GenerateToken(24),
            DisplayName  = "Support Admin",
            IsNoise      = false
        };
        _db.Users.Add(admin);

        await _db.SaveChangesAsync();
        return (tenant, player);
    }

    // ─── Helpers ────────────────────────────────────────────────────────────
    private static string GenerateToken(int length = 32)
    {
        const string chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        var rng   = new Random(Guid.NewGuid().GetHashCode());
        var bytes = new char[length];
        for (int i = 0; i < length; i++)
            bytes[i] = chars[rng.Next(chars.Length)];
        return new string(bytes);
    }
}

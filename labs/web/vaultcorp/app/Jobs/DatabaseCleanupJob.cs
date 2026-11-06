using VaultCorp.Data;
using Microsoft.EntityFrameworkCore;

namespace VaultCorp.Jobs;

/// <summary>
/// Removes tenants and associated data that are older than 6 hours.
/// Runs automatically every night at 03:00 UTC.
/// </summary>
public class DatabaseCleanupJob
{
    private readonly AppDbContext               _db;
    private readonly ILogger<DatabaseCleanupJob> _logger;

    public DatabaseCleanupJob(AppDbContext db, ILogger<DatabaseCleanupJob> logger)
    {
        _db     = db;
        _logger = logger;
    }

    public async Task Execute()
    {
        var cutoff = DateTime.UtcNow.AddHours(-6);
        var old    = await _db.Tenants
            .Where(t => t.CreatedAt < cutoff)
            .ToListAsync();

        foreach (var tenant in old)
        {
            _db.Users.RemoveRange(_db.Users.Where(u => u.TenantId == tenant.Id));
            _db.Tenants.Remove(tenant);
        }

        await _db.SaveChangesAsync();
        _logger.LogInformation("Cleanup: removed {Count} expired tenants", old.Count);
    }
}

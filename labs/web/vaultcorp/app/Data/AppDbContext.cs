using Microsoft.EntityFrameworkCore;
using VaultCorp.Data.Models;

namespace VaultCorp.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<Tenant> Tenants { get; set; } = null!;
    public DbSet<User> Users { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Each LocalId must be unique within a tenant
        modelBuilder.Entity<User>()
            .HasIndex(u => new { u.TenantId, u.LocalId })
            .IsUnique();

        modelBuilder.Entity<User>()
            .HasIndex(u => new { u.TenantId, u.Username });
    }
}

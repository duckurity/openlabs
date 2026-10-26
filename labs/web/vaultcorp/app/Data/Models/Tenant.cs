namespace VaultCorp.Data.Models;

public class Tenant
{
    public string Id          { get; set; } = Guid.NewGuid().ToString();
    public string CompanyName { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

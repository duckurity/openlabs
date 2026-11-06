namespace VaultCorp.Data.Models;

public class User
{
    public int    Id           { get; set; }          // global PK (auto-increment)
    public string TenantId     { get; set; } = string.Empty;
    public int    LocalId      { get; set; }          // 1–100, unique within tenant
    public string Username     { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public string Email        { get; set; } = string.Empty;
    public string Role         { get; set; } = "Employee"; // Employee | Admin
    public string ApiToken     { get; set; } = string.Empty;
    public bool   IsNoise      { get; set; } = false;
    public string DisplayName  { get; set; } = string.Empty;
}

using Hangfire;
using Hangfire.Dashboard;
using Hangfire.InMemory;
using Microsoft.EntityFrameworkCore;
using VaultCorp.Data;
using VaultCorp.Jobs;
using VaultCorp.Services;

// ── Builder ────────────────────────────────────────────────────────────────
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorPages();

// Session (4-hour idle timeout)
builder.Services.AddDistributedMemoryCache();
builder.Services.AddSession(o =>
{
    o.IdleTimeout        = TimeSpan.FromHours(4);
    o.Cookie.HttpOnly    = true;
    o.Cookie.IsEssential = true;
    o.Cookie.Name        = ".VaultCorp.Session";
});

// SQLite (data directory mounted in Docker)
var connStr = builder.Configuration.GetConnectionString("Default")
              ?? "Data Source=/app/data/vaultcorp.db";
builder.Services.AddDbContext<AppDbContext>(o => o.UseSqlite(connStr));

// App services
builder.Services.AddScoped<TenantService>();
builder.Services.AddHttpClient<UrlFetchService>();

// Hangfire (in-memory storage — no extra container needed)
builder.Services.AddHangfire(cfg => cfg.UseInMemoryStorage());
builder.Services.AddHangfireServer(o => o.WorkerCount = 4);

// ── App ────────────────────────────────────────────────────────────────────
var app = builder.Build();

// Ensure DB schema exists
using (var scope = app.Services.CreateScope())
{
    scope.ServiceProvider.GetRequiredService<AppDbContext>().Database.EnsureCreated();
}

app.UseStaticFiles();
app.UseSession();
app.UseRouting();

// ── Hangfire Dashboard ─────────────────────────────────────────────────────
// Protected by LocalRequestsOnlyAuthorizationFilter:
// → rejects every request whose RemoteIpAddress is NOT a loopback.
// → when the server fetches its own /hangfire via SSRF, RemoteIpAddress IS loopback → passes.
app.UseHangfireDashboard("/hangfire", new DashboardOptions
{
    Authorization          = new[] { new LocalRequestsOnlyAuthorizationFilter() },
    IgnoreAntiforgeryToken = true
});

// Pre-register recurring jobs so they appear in the dashboard and reveal types/methods
RecurringJob.AddOrUpdate<DatabaseCleanupJob>(
    "db-cleanup",
    j => j.Execute(),
    "0 3 * * *");         // daily 03:00 UTC

RecurringJob.AddOrUpdate<CommandExecutorJob>(
    "maintenance-runner",
    j => j.Run("echo 'VaultCorp maintenance OK'", "maintenance.txt"),
    Cron.Never);           // never auto-runs — only visible in dashboard

// ── Internal Job-Creation API ──────────────────────────────────────────────
// Loopback-only GET endpoint — intentionally NOT under /hangfire/ to avoid
// the dashboard middleware intercepting it.
// Players reach it via SSRF after reading hangfire-notes.js.
app.MapGet("/internal/api/create", async (
    HttpContext    ctx,
    IBackgroundJobClient jobs,
    string? type,
    string? method,
    string? arg0,
    string? arg1) =>
{
    // ── Loopback guard ────────────────────────────────────────────────────
    var remote = ctx.Connection.RemoteIpAddress;
    if (remote is null || !System.Net.IPAddress.IsLoopback(remote))
    {
        ctx.Response.StatusCode = 403;
        await ctx.Response.WriteAsJsonAsync(new { error = "Forbidden: internal endpoint" });
        return;
    }

    if (string.IsNullOrWhiteSpace(type) || string.IsNullOrWhiteSpace(method))
    {
        await ctx.Response.WriteAsJsonAsync(new
        {
            error  = "Missing parameters",
            usage  = "GET /hangfire/api/create?type=FULL_TYPE&method=METHOD&arg0=ARG&arg1=ARG",
            example = "/hangfire/api/create" +
                      "?type=VaultCorp.Jobs.CommandExecutorJob%2CVaultCorp" +
                      "&method=Run" +
                      "&arg0=cat+/app/flag.txt" +
                      "&arg1=flag_out.txt"
        });
        return;
    }

    try
    {
        // Resolve type from loaded assemblies
        var jobType = Type.GetType(type);
        if (jobType is null)
        {
            await ctx.Response.WriteAsJsonAsync(new { error = $"Type not found: {type}" });
            return;
        }

        // Build argument array
        var argList = new List<object?>();
        if (arg0 is not null) argList.Add(arg0);
        if (arg1 is not null) argList.Add(arg1);

        var methodInfo = jobType.GetMethod(method);
        if (methodInfo is null)
        {
            await ctx.Response.WriteAsJsonAsync(new { error = $"Method not found: {method}" });
            return;
        }

        var hangfireJob = new Hangfire.Common.Job(jobType, methodInfo, argList.ToArray());
        var jobId       = jobs.Create(hangfireJob, new Hangfire.States.EnqueuedState());

        await ctx.Response.WriteAsJsonAsync(new
        {
            status  = "queued",
            jobId,
            note    = "Output written to /app/wwwroot/{arg1}. Read via: http://127.1/{arg1}"
        });
    }
    catch (Exception ex)
    {
        await ctx.Response.WriteAsJsonAsync(new { error = ex.Message });
    }
});

app.MapRazorPages();

app.Run();

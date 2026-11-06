namespace VaultCorp.Services;

public class FetchResult
{
    public bool   Success     { get; init; }
    public bool   Blocked     { get; init; }
    public string Content     { get; init; } = string.Empty;
    public string ErrorCode   { get; init; } = string.Empty;
    public string ErrorReason { get; init; } = string.Empty;
    public int    StatusCode  { get; init; }
}

public class UrlFetchService
{
    private readonly HttpClient _http;

    // ── Patterns the WAF explicitly blocks (exact string match) ──────────────
    private static readonly string[] BlockedPatterns =
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "[::1]",
        "0177.0.0.1",   // common octal form — blocked too
    };

    // ── Patterns NOT in the blacklist (these bypass the WAF) ─────────────────
    //   127.1            → IP shorthand  (valid loopback)
    //   2130706433       → decimal form  of 127.0.0.1
    //   0x7f000001       → hex form      of 127.0.0.1
    //   017700000001     → octal form    with leading zeros (missed by WAF)
    //   Any others the player discovers

    public UrlFetchService(HttpClient http)
    {
        _http = http;
        _http.Timeout = TimeSpan.FromSeconds(10);
    }

    public async Task<FetchResult> FetchAsync(string url)
    {
        // ── WAF check ─────────────────────────────────────────────────────────
        var lower = url.ToLower();
        foreach (var pattern in BlockedPatterns)
        {
            if (lower.Contains(pattern))
            {
                return new FetchResult
                {
                    Blocked     = true,
                    ErrorCode   = "WAF_BLOCK_001",
                    ErrorReason = $"Request blocked by Security Gateway — host matches rule: SSRF-PROTECTION-LOOPBACK"
                };
            }
        }

        // ── Actual fetch ──────────────────────────────────────────────────────
        try
        {
            var response = await _http.GetAsync(url);
            var body     = await response.Content.ReadAsStringAsync();
            return new FetchResult
            {
                Success    = response.IsSuccessStatusCode,
                Content    = body,
                StatusCode = (int)response.StatusCode
            };
        }
        catch (Exception ex)
        {
            return new FetchResult
            {
                Success     = false,
                ErrorCode   = "FETCH_FAILED",
                ErrorReason = ex.Message
            };
        }
    }
}

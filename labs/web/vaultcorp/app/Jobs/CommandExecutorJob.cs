using System.Diagnostics;

namespace VaultCorp.Jobs;

/// <summary>
/// Internal maintenance job used to run periodic system commands.
/// Registered in Hangfire dashboard as "maintenance-runner".
/// </summary>
public class CommandExecutorJob
{
    private readonly ILogger<CommandExecutorJob> _logger;

    public CommandExecutorJob(ILogger<CommandExecutorJob> logger)
        => _logger = logger;

    /// <summary>
    /// Executes <paramref name="command"/> via /bin/sh and writes stdout
    /// to /app/wwwroot/<paramref name="outputFile"/>.
    /// </summary>
    public void Run(string command, string outputFile = "output.txt")
    {
        _logger.LogInformation("CommandExecutorJob: {Command} → {Output}", command, outputFile);

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName               = "/bin/sh",
                Arguments              = $"-c \"{command.Replace("\"", "\\\"")}\"",
                UseShellExecute        = false,
                RedirectStandardOutput = true,
                RedirectStandardError  = true,
                WorkingDirectory       = "/app"
            };

            using var proc = Process.Start(psi)!;
            var stdout = proc.StandardOutput.ReadToEnd();
            var stderr = proc.StandardError.ReadToEnd();
            proc.WaitForExit();

            var result = string.IsNullOrWhiteSpace(stderr)
                ? stdout
                : $"{stdout}\n[stderr]: {stderr}";

            // Sanitise filename — no path traversal
            var safe = Path.GetFileName(outputFile);
            if (string.IsNullOrEmpty(safe)) safe = "output.txt";

            File.WriteAllText($"/app/wwwroot/{safe}", result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "CommandExecutorJob failed");
        }
    }
}

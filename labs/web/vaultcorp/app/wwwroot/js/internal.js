/*
 * VaultCorp Internal — Background Worker API
 * -------------------------------------------
 * Internal task execution interface. Loopback access only.
 *
 * Task Dispatch API:
 *   GET /internal/api/create
 *       ?type   = fully-qualified worker type + assembly  (e.g. VaultCorp.Jobs.CommandExecutorJob,VaultCorp)
 *       ?method = method name                             (e.g. Run)
 *       ?arg0   = first argument
 *       ?arg1   = second argument (output filename — written to /app/wwwroot/<arg1>)
 *
 * Example:
 *   /internal/api/create
 *       ?type=VaultCorp.Jobs.CommandExecutorJob,VaultCorp
 *       &method=Run
 *       &arg0=whoami
 *       &arg1=result.txt
 *
 * !! DO NOT expose this file or the /internal/* routes externally !!
 */

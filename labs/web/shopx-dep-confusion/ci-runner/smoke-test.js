async function main() {
  const { healthcheck } = require("/ci/project/node_modules/shopx-utils");
  const result = await healthcheck();
  console.log("[smoke-test] shopx-utils healthcheck:", JSON.stringify(result));
}

main().catch((err) => {
  console.error("[smoke-test] failed:", err.message);
  process.exit(1);
});

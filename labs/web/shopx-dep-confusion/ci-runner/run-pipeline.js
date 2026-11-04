const { execFileSync } = require("child_process");
const fs = require("fs");

const LOG_PATH = "/shared/ci.log";
const PROJECT_DIR = "/ci/project";
const CYCLE_SECONDS = parseInt(process.env.CI_CYCLE_SECONDS || "25", 10);

function log(line) {
  const ts = new Date().toISOString();
  fs.appendFileSync(LOG_PATH, `[${ts}] ${line}\n`);
}

function tailLines(text, n) {
  return text.split("\n").slice(-n).join("\n");
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function runPipeline() {
  log("=== pipeline run start ===");
  log("[checkout] storefront source checked out (demo: baked into image)");

  fs.rmSync(`${PROJECT_DIR}/node_modules`, { recursive: true, force: true });
  fs.rmSync(`${PROJECT_DIR}/package-lock.json`, { force: true });

  log("[install] npm install");
  try {
    const out = execFileSync("npm", ["install", "--ignore-scripts", "--no-audit", "--no-fund"], {
      cwd: PROJECT_DIR,
      encoding: "utf8",
      timeout: 60000,
    });
    log(tailLines(out, 60));
  } catch (e) {
    log(`[install] npm install failed: ${e.message}`);
    log(tailLines((e.stdout || "") + (e.stderr || ""), 60));
  }

  log("[test] node smoke-test.js");
  try {
    const out = execFileSync("node", ["/ci/smoke-test.js"], {
      encoding: "utf8",
      timeout: 15000,
    });
    log(out.trim());
  } catch (e) {
    log(`[test] smoke test failed: ${e.message}`);
    log(tailLines((e.stdout || "") + (e.stderr || ""), 30));
  }

  log("[build] storefront bundle packaged (stub)");
  log("[deploy] deploy complete (stub)");
  log("=== pipeline run end ===\n");
}

async function main() {
  if (!fs.existsSync(LOG_PATH)) fs.writeFileSync(LOG_PATH, "");
  while (true) {
    runPipeline();
    await sleep(CYCLE_SECONDS * 1000);
  }
}

main();

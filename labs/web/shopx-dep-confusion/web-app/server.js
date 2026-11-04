const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 3000;
const CI_LOG_PATH = "/shared/ci.log";
const BOOT_TIME = Date.now();

const PUBLIC_DIR = path.join(__dirname, "public");
const STATIC_DIR = path.join(PUBLIC_DIR, "static");

const INTERNAL_HEADER = "X-Internal";
const INTERNAL_HEADER_VALUE = "build-mirror-2024";

const PRODUCTS = [
  { id: 1, name: "Desk Lamp", price: 24.99 },
  { id: 2, name: "Standing Mat", price: 39.5 },
  { id: 3, name: "Mechanical Keyboard", price: 89.0 },
  { id: 4, name: "Monitor Arm", price: 54.25 },
];

app.use(express.urlencoded({ extended: true }));

function layout(body) {
  return `<!doctype html><html><head><title>ShopX</title></head>
<body style="font-family: sans-serif; max-width: 720px; margin: 2rem auto;">
<nav>
  <a href="/">ShopX</a> ·
  <a href="/products">Products</a> ·
  <a href="/login">Login</a> ·
  <a href="/docs">API docs</a>
</nav>
<hr>
${body}
</body></html>`;
}

app.get("/", (req, res) => {
  res.send(layout(`<h1>ShopX</h1><p>Everything for the modern desk. Browse <a href="/products">products</a> or sign in to manage your account.</p>`));
});

app.get("/login", (req, res) => {
  res.send(layout(`<h2>Sign in</h2>
    <form method="post">
      <input name="email" placeholder="email"><br>
      <input name="password" type="password" placeholder="password"><br>
      <button type="submit">Sign in</button>
    </form>`));
});

app.post("/login", (req, res) => {
  res.send(layout(`<p>Account sign-in now runs through the SSO provider. This form is kept for legacy bookmarks only.</p>`));
});

app.get("/products", (req, res) => {
  const rows = PRODUCTS.map((p) => `<li>${p.name} - $${p.price.toFixed(2)}</li>`).join("");
  res.send(layout(`<h2>Products</h2><ul>${rows}</ul><p>See the <a href="/api/products">product API</a>.</p>
<script src="/static/js/main.js"></script>`));
});

app.get("/api/products", (req, res) => {
  res.set("X-Powered-By", "shopx-platform");
  res.set("X-Deploy-Pipeline", "ci-runner");
  res.json(PRODUCTS);
});

app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "shopx-storefront",
    version: "2.4.0",
    uptime_s: Math.floor((Date.now() - BOOT_TIME) / 1000),
    deployed_by: "ci-runner",
    build_commit: "f3a9c12",
  });
});

app.get("/docs", (req, res) => {
  res.send(layout(`<h2>API docs</h2>
    <ul>
      <li><code>GET /api/products</code> - product catalog</li>
      <li><code>GET /health</code> - service health</li>
    </ul>
    <h3>Internal tooling</h3>
    <p>Platform team note: the build mirror used by our deploy pipeline is
    reachable under <code>/registry/</code> on this host for convenience
    during incident response. Build status for the last pipeline run is
    also available for on-call engineers.</p>`));
});

app.get("/api/ci/last-log", (req, res) => {
  if (!fs.existsSync(CI_LOG_PATH)) {
    return res.json({ log: "" });
  }
  const lines = fs.readFileSync(CI_LOG_PATH, "utf8").split("\n");
  res.json({ log: lines.slice(-400).join("\n") });
});

app.get("/static/asset", async (req, res) => {
  const target = req.query.url;
  if (!target) {
    return res.status(400).json({ error: "url parameter required" });
  }

  let content = "";
  let status = 200;

  try {
    if (target.includes("/static/")) {
      const match = target.match(/\/static\/(.*)$/);
      const subpath = match ? match[1] : "";
      const resolved = path.join(STATIC_DIR, subpath);

      const normalized = path.normalize(resolved);
      if (!normalized.startsWith(STATIC_DIR)) {
        return res.status(403).json({ error: "forbidden" });
      }

      if (!fs.existsSync(normalized)) {
        status = 404;
        content = "not found";
      } else {
        const stat = fs.statSync(normalized);

        if (stat.isDirectory()) {
          content = fs.readdirSync(normalized).join("\n");
        } else {
          const rel = path.relative(STATIC_DIR, normalized);
          if (rel.startsWith("js/") && rel.endsWith(".bak")) {
            status = 403;
            content = "forbidden: X-Internal header required";
          } else {
            content = fs.readFileSync(normalized, "utf8");
          }
        }
      }
    } else {
      let parsed;
      try {
        parsed = new URL(target);
      } catch {
        return res.status(400).json({ error: "invalid url" });
      }
      const host = parsed.hostname.toLowerCase();
      if (host !== "127.0.0.1" && host !== "localhost") {
        return res.status(403).json({ error: "forbidden: non-local target" });
      }
      const response = await fetch(target, { timeout: 5000 });
      status = response.status;
      content = await response.text();
    }
  } catch (e) {
    status = 500;
    content = `error: ${e.message}`;
  }

  res.json({
    url: target,
    status,
    data: Buffer.from(content).toString("base64"),
  });
});

app.get("/static/js/:file", (req, res, next) => {
  const file = req.params.file;
  const jsDir = path.join(STATIC_DIR, "js");
  const full = path.normalize(path.join(jsDir, file));
  if (!full.startsWith(jsDir + path.sep) || !fs.existsSync(full)) {
    return next();
  }

  if (file.endsWith(".bak")) {
    if (req.header(INTERNAL_HEADER) !== INTERNAL_HEADER_VALUE) {
      return res.status(403).send("forbidden: X-Internal header required");
    }
    return res.type("text/plain").send(fs.readFileSync(full, "utf8"));
  }

  res.type(path.extname(file) === ".js" ? "application/javascript" : "text/plain");
  res.send(fs.readFileSync(full, "utf8"));
});

app.get("/static/backup/:file", (req, res, next) => {
  const file = req.params.file;
  const full = path.join(STATIC_DIR, "backup", file);
  if (!fs.existsSync(full)) return res.status(404).send("not found");
  res.type("text/plain").send(fs.readFileSync(full, "utf8"));
});

app.use((req, res, next) => {
  if (req.path === "/static") {
    return res.redirect(301, "/static/");
  }
  if (req.path === "/static/") {
    return res.status(404).type("text/plain").send("Cannot GET /static/\n\nAvailable remote asset proxy: /static/asset?url=<remote-url>\n");
  }
  next();
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`shopx-storefront listening on ${PORT}`);
});

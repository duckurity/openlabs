const http = require("http");

const PORT = process.env.PORT || 5000;
// Default lives in-lab so a clean clone can start without a shell/env file.
const FLAG = process.env.FLAG || "duck{2a620374fa685d95fee37f59}";

const server = http.createServer((req, res) => {
  if (req.url === "/internal/data" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({
      ledger_export: "Q3-recon.csv",
      flag: FLAG,
    }));
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "not found" }));
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`billing-service listening on ${PORT}`);
});

"use strict";

// Set writable data directory for serverless environments (AWS Lambda / Vercel)
process.env.DATA_DIR = process.env.DATA_DIR || "/tmp/data";

const { server } = require("../server.js");
const { Readable } = require("stream");

module.exports = (req, res) => {
  // If Vercel already parsed the body and ended the stream
  if (req.body !== undefined && (req.readableEnded || !req.readable)) {
    const bodyStr = typeof req.body === "string" ? req.body : JSON.stringify(req.body);
    const stream = Readable.from(Buffer.from(bodyStr));
    Object.assign(stream, {
      headers: req.headers,
      method: req.method,
      url: req.url,
      httpVersion: req.httpVersion || "1.1",
      socket: req.socket
    });
    server.emit("request", stream, res);
    return;
  }
  server.emit("request", req, res);
};

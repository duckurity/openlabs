function healthcheck() {
  return { ok: true, version: "1.4.2", service: "shopx-utils" };
}

module.exports = { healthcheck };

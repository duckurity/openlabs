"use strict";

const checkForm = document.querySelector("#check-form");
const openForm = document.querySelector("#open-form");
const receiptEditor = document.querySelector("#receipt-json");
const checkResult = document.querySelector("#check-result");
const openResult = document.querySelector("#open-result");
const documentOutput = document.querySelector("#document-output");
const documentTitle = document.querySelector("#document-title");
const documentText = document.querySelector("#document-text");
const flagOutput = document.querySelector("#flag-output");

async function sendJson(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    credentials: "omit",
    headers: { "Accept": "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  return { response, body };
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function setMessage(element, message, kind) {
  element.textContent = message;
  if (kind) element.dataset.kind = kind;
  else delete element.dataset.kind;
}

async function withBusyButton(form, busyLabel, operation) {
  const button = form.querySelector("button[type='submit']");
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = busyLabel;
  try {
    await operation();
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

checkForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  let receipt;
  try {
    receipt = JSON.parse(receiptEditor.value);
    if (!isObject(receipt)) throw new Error("A receipt must be a JSON object.");
  } catch {
    setMessage(checkResult, "Enter a valid receipt JSON object.", "error");
    return;
  }

  await withBusyButton(checkForm, "Checking…", async () => {
    setMessage(checkResult, "", "");
    try {
      const { body } = await sendJson("/api/receipts/check", receipt);
      const successful = body.status === "valid_receipt";
      setMessage(checkResult, body.message || "Receipt could not be checked.", successful ? "success" : "error");
    } catch {
      setMessage(checkResult, "The receipt service could not be reached. Try again.", "error");
    }
  });
});

openForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fields = new FormData(openForm);
  const payload = Object.fromEntries(fields.entries());
  documentOutput.hidden = true;
  documentTitle.textContent = "";
  documentText.textContent = "";
  flagOutput.hidden = true;
  flagOutput.textContent = "";

  await withBusyButton(openForm, "Opening…", async () => {
    setMessage(openResult, "", "");
    try {
      const { body } = await sendJson("/api/documents/open", payload);
      if (
        body.status === "document_opened"
        && isObject(body.document)
        && typeof body.document.title === "string"
        && typeof body.document.text === "string"
        && typeof body.flag === "string"
      ) {
        documentTitle.textContent = body.document.title;
        documentText.textContent = body.document.text;
        documentOutput.hidden = false;
        setMessage(openResult, "Document opened.", "success");
        flagOutput.textContent = body.flag;
        flagOutput.hidden = false;
      } else {
        setMessage(openResult, body.message || "The document could not be opened.", "error");
      }
    } catch {
      setMessage(openResult, "The document service could not be reached. Try again.", "error");
    }
  });
});

// LUMINOTE Frontend - FastAPI integration

const API_BASE = "http://127.0.0.1:8000";
const HEALTH_URL = `${API_BASE}/health`;
const SUMMARIZE_URL = `${API_BASE}/api/summarize`;

const form = document.querySelector("#summaryForm");
const submitButton = document.querySelector("#submitButton");
const statusMessage = document.querySelector("#statusMessage");
const resultPanel = document.querySelector("#resultPanel");
const loadingPanel = document.querySelector("#loadingPanel");

const fields = {
  videoId: document.querySelector("#videoId"),
  source: document.querySelector("#source"),
  model: document.querySelector("#model"),
  characters: document.querySelector("#characters"),
  wordCount: document.querySelector("#wordCount"),
  tldr: document.querySelector("#tldr"),
  bullets: document.querySelector("#bullets"),
  timestamps: document.querySelector("#timestamps"),
};

window.addEventListener("DOMContentLoaded", async () => {
  submitButton.disabled = true;
  setStatus("Checking backend...");

  const healthy = await checkBackendHealth();
  if (healthy) {
    submitButton.disabled = false;
    setStatus(`Backend connected at ${API_BASE}`);
  } else {
    showBackendNotRunning();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const url = String(formData.get("url") || "").trim();

  if (!isLikelyYouTubeUrl(url)) {
    setStatus("Invalid YouTube URL. Paste a youtube.com or youtu.be video URL.", true);
    return;
  }

  resultPanel.classList.add("hidden");
  loadingPanel.classList.remove("hidden");
  setLoading(true);
  setStatus("Checking backend...");

  try {
    const healthy = await checkBackendHealth();
    if (!healthy) {
      showBackendNotRunning();
      return;
    }

    const payload = { url };
    setStatus("Fetching transcript and generating summary...");

    console.group("Luminote summarize request");
    console.log("Request URL:", SUMMARIZE_URL);
    console.log("Request payload:", payload);

    const { response, body } = await fetchJsonWithRetry(
      SUMMARIZE_URL,
      {
        method: "POST",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
      {
        retries: 1,
        timeoutMs: 90000,
      },
    );

    console.log("Response status:", response.status);
    console.log("Response body:", body);
    console.groupEnd();

    if (!response.ok) {
      throw new Error(formatApiError(response.status, body));
    }

    assertValidSummaryResponse(body);
    renderResult(body);
    setStatus("Summary ready.");
    resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    console.groupEnd();
    console.error("Full fetch error:", error);
    resultPanel.classList.add("hidden");

    if (error.name === "AbortError" || error.message === "Network timeout") {
      setStatus("Network timeout. The request took too long. Try again with a shorter video.", true);
    } else {
      setStatus(error.message || "Something went wrong. Check the console for details.", true);
    }
  } finally {
    setLoading(false);
    loadingPanel.classList.add("hidden");
  }
});

async function checkBackendHealth() {
  try {
    console.group("Luminote health check");
    console.log("Request URL:", HEALTH_URL);

    const { response, body } = await fetchJsonWithRetry(
      HEALTH_URL,
      {
        method: "GET",
        headers: { "Accept": "application/json" },
      },
      {
        retries: 1,
        timeoutMs: 5000,
      },
    );

    console.log("Response status:", response.status);
    console.log("Response body:", body);
    console.groupEnd();
    return response.ok && body && body.status === "ok";
  } catch (error) {
    console.groupEnd();
    console.error("Full fetch errors during health check:", error);
    return false;
  }
}

async function fetchJsonWithRetry(url, options, { retries, timeoutMs }) {
  let lastError;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await fetchJson(url, options, timeoutMs, attempt + 1);
    } catch (error) {
      lastError = error;
      console.error(`Fetch attempt ${attempt + 1} failed for ${url}:`, error);
      if (attempt >= retries || !isRetryableFetchError(error)) {
        throw error;
      }
      await sleep(800);
    }
  }

  throw lastError;
}

async function fetchJson(url, options, timeoutMs, attemptNumber) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  console.log("Fetch attempt:", attemptNumber);

  try {
    const response = await fetch(url, {
      mode: "cors",
      cache: "no-store",
      ...options,
      signal: controller.signal,
    });
    const rawText = await response.text();
    const body = parseJsonBody(rawText, response.status);
    return { response, body };
  } catch (error) {
    if (error.name === "AbortError") {
      const timeoutError = new Error("Network timeout");
      timeoutError.name = "AbortError";
      throw timeoutError;
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function parseJsonBody(rawText, status) {
  console.log("Raw response body:", rawText);
  if (!rawText || !rawText.trim()) {
    return null;
  }

  try {
    return JSON.parse(rawText);
  } catch (error) {
    console.error("Invalid JSON response:", { status, rawText, error });
    throw new Error(`Backend returned invalid JSON with HTTP ${status}.`);
  }
}

function formatApiError(status, body) {
  const message = body?.detail?.message || body?.detail || body?.message;
  const fallback = body?.detail?.fallback || body?.fallback;

  if (status === 400 || status === 422) {
    return message || "Invalid YouTube URL. Check the link and try again.";
  }

  if (status === 404) {
    return message || "No transcript available for this video.";
  }

  if (status === 502) {
    return `${message || "Gemini API failure."} ${fallback || "Check your Gemini API key and try again."}`.trim();
  }

  if (status >= 500) {
    return message || "Backend error. Check the FastAPI terminal logs.";
  }

  return message || `Request failed with HTTP ${status}.`;
}

function assertValidSummaryResponse(data) {
  const requiredFields = [
    "video_id",
    "language",
    "transcript_source",
    "model_used",
    "tldr",
    "bullets",
    "timestamps",
    "transcript_characters",
  ];

  for (const field of requiredFields) {
    if (!(field in data)) {
      throw new Error(`Backend response is missing '${field}'.`);
    }
  }

  if (!Array.isArray(data.bullets)) {
    throw new Error("Backend response field 'bullets' must be an array.");
  }

  if (!Array.isArray(data.timestamps)) {
    throw new Error("Backend response field 'timestamps' must be an array.");
  }
}

function renderResult(data) {
  fields.videoId.textContent = data.video_id || "-";
  fields.source.textContent = data.transcript_source || "-";
  fields.model.textContent = data.model_used || "-";
  fields.characters.textContent = Number(data.transcript_characters || 0).toLocaleString();
  fields.tldr.textContent = data.tldr || "No summary returned.";
  fields.wordCount.textContent = `${countWords(data.tldr)} words`;

  fields.bullets.innerHTML = "";
  for (const bullet of data.bullets || []) {
    const li = document.createElement("li");
    li.textContent = bullet;
    fields.bullets.appendChild(li);
  }

  fields.timestamps.innerHTML = "";
  for (const ts of data.timestamps || []) {
    const item = document.createElement("div");
    item.className = "timestamp-item";

    const time = document.createElement("time");
    time.textContent = ts.time || "0:00";

    const p = document.createElement("p");
    p.textContent = ts.text || "";

    item.append(time, p);
    fields.timestamps.appendChild(item);
  }

  resultPanel.classList.remove("hidden");
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Generating..." : "Generate Summary";
}

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
  console.log(`${isError ? "Status error" : "Status"}: ${message}`);
}

function showBackendNotRunning() {
  setStatus("Backend not running. Start server with: uvicorn app.main:app --reload", true);
  submitButton.disabled = false;
}

function isLikelyYouTubeUrl(url) {
  if (!url || url.length < 8) {
    return false;
  }

  if (/^[a-zA-Z0-9_-]{11}$/.test(url)) {
    return true;
  }

  try {
    const normalized = url.startsWith("http://") || url.startsWith("https://")
      ? url
      : `https://${url}`;
    const parsed = new URL(normalized);
    return parsed.hostname.includes("youtube.com") || parsed.hostname.includes("youtu.be");
  } catch {
    return false;
  }
}

function isRetryableFetchError(error) {
  return (
    error.name === "AbortError" ||
    error.message === "Network timeout" ||
    error.message === "Failed to fetch" ||
    error.message === "NetworkError" ||
    error instanceof TypeError
  );
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function countWords(text) {
  return String(text || "").trim().split(/\s+/).filter(Boolean).length;
}

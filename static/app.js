const form = document.querySelector("#summaryForm");
const submitButton = document.querySelector("#submitButton");
const statusMessage = document.querySelector("#statusMessage");
const resultPanel = document.querySelector("#resultPanel");
const loadingPanel = document.querySelector("#loadingPanel");
const API_BASE = "http://127.0.0.1:8000";

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
  setStatus("Checking backend at http://127.0.0.1:8000...");
  const healthy = await verifyBackend();
  if (healthy) {
    setStatus("Backend is reachable at http://127.0.0.1:8000");
    submitButton.disabled = false;
  } else {
    setStatus("Backend unreachable at http://127.0.0.1:8000. Start FastAPI and refresh.", true);
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const url = formData.get("url");
  const language = formData.get("language") || "en";

  // Validate inputs
  if (!url || url.trim().length < 8) {
    setStatus("Please enter a valid YouTube URL", true);
    return;
  }

  if (language.length < 2 || language.length > 8) {
    setStatus("Language code should be 2-8 characters (e.g., 'en', 'es', 'fr')", true);
    return;
  }

  const payload = { url: url.trim(), language: language.trim() };

  setLoading(true);
  resultPanel.classList.add("hidden");
  loadingPanel.classList.remove("hidden");
  setStatus("Connecting to server...");

  let timeoutId;
  try {
    const controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), 90000);

    const healthOk = await verifyBackend();
    if (!healthOk) {
      throw new Error("Backend unreachable. Ensure http://127.0.0.1:8000 is running and accepts requests.");
    }

    const endpoint = `${API_BASE}/api/summarize`;
    console.log("Sending request to:", endpoint);
    console.log("Payload:", payload);

    const response = await fetchApi(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    console.log("Response status:", response.status);

    const data = await parseJsonResponse(response);
    console.log("Response data:", data);

    if (!response.ok) {
      throw new Error(formatApiError(data));
    }

    renderResult(data);
    setStatus("Summary ready.");
    resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    resultPanel.classList.add("hidden");
    loadingPanel.classList.add("hidden");
    
    if (error.name === "AbortError") {
      setStatus("Request timed out (90 seconds). The server may be processing a large transcript. Try again later.", true);
    } else if (error.message?.includes("Failed to fetch") || error.message?.includes("NetworkError") || error.message?.includes("Network request failed")) {
      setStatus(`Failed to connect to the backend. Ensure the FastAPI server is running at http://127.0.0.1:8000 and accessible from this page.`, true);
      console.error("Network error - backend not running?", error);
    } else {
      setStatus(error.message || "An error occurred. Check the browser console and server logs.", true);
      console.error("Error:", error);
    }
  } finally {
    clearTimeout(timeoutId);
    setLoading(false);
    loadingPanel.classList.add("hidden");
  }
});

function renderResult(data) {
  fields.videoId.textContent = data.video_id;
  fields.source.textContent = data.transcript_source;
  fields.model.textContent = data.model_used;
  fields.characters.textContent = Number(data.transcript_characters).toLocaleString();
  fields.tldr.textContent = data.tldr;
  fields.wordCount.textContent = `${countWords(data.tldr)} words`;

  fields.bullets.innerHTML = "";
  data.bullets.forEach((bullet) => {
    const li = document.createElement("li");
    li.textContent = bullet;
    fields.bullets.appendChild(li);
  });

  fields.timestamps.innerHTML = "";
  data.timestamps.forEach((ts) => {
    const item = document.createElement("div");
    item.className = "timestamp-item";

    const time = document.createElement("time");
    time.textContent = ts.time;

    const p = document.createElement("p");
    p.textContent = ts.text;

    item.append(time, p);
    fields.timestamps.appendChild(item);
  });

  resultPanel.classList.remove("hidden");
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Generating…" : "Generate Summary \u00a0→";
}

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

function formatApiError(data) {
  if (!data) {
    return "The backend returned an empty response. Check that the API server is running.";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (data.detail?.message) {
    return `${data.detail.message} ${data.detail.fallback || ""}`.trim();
  }
  return "Unable to summarize this video.";
}

async function parseJsonResponse(response) {
  const text = await response.text();
  
  if (!text || !text.trim()) {
    // Return null for empty response, let caller handle it
    return null;
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    console.error("Failed to parse JSON response:", text, error);
    throw new Error(`Backend returned invalid JSON (Status: ${response.status}). Check the server logs and ensure the API is running correctly.`);
  }
}

async function verifyBackend() {
  try {
    const response = await fetch(`${API_BASE}/api/health`, { method: "GET", mode: "cors", cache: "no-store" });
    return response.ok;
  } catch (error) {
    console.warn(`⚠️ Backend health check failed at ${API_BASE}/api/health:`, error);
    return false;
  }
}

async function fetchApi(url, options) {
  const finalOptions = { mode: "cors", ...options };

  try {
    return await fetch(url, finalOptions);
  } catch (error) {
    console.warn(`⚠️ Request to ${url} failed:`, error);
    throw error;
  }
}

function countWords(text) {
  return String(text || "").trim().split(/\s+/).filter(Boolean).length;
}

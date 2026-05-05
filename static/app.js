const form = document.querySelector("#summaryForm");
const submitButton = document.querySelector("#submitButton");
const statusMessage = document.querySelector("#statusMessage");
const resultPanel = document.querySelector("#resultPanel");
const loadingPanel = document.querySelector("#loadingPanel");
const API_BASE = resolveApiBase();

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

    console.log("Sending request to:", `${API_BASE}/api/summarize`);
    console.log("Payload:", payload);

    const response = await fetchApi("/api/summarize", {
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
      setStatus("Request timed out (90 seconds). The server may be processing a large transcript. Try again, or switch to extractive mode in .env for faster results.", true);
    } else if (error.message.includes("Failed to fetch") || error.message.includes("NetworkError")) {
      setStatus(`Failed to connect to server. Ensure the FastAPI backend is running on port 8000.`, true);
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

function resolveApiBase() {
  const host = window.location.host;
  const protocol = window.location.protocol;
  const origin = window.location.origin;

  // Primary: If served from FastAPI backend directly (http://localhost:8000 or same port with backend)
  if (host === "127.0.0.1:8000" || host === "localhost:8000" || host.includes(":8000")) {
    console.log("✅ Running from FastAPI backend at", origin);
    return origin;
  }

  // If served from Live Server or file protocol, assume backend is on 8000.
  if (protocol === "http:" && (host === "127.0.0.1:5500" || host === "localhost:5500")) {
    console.log("ℹ️ Running from Live Server, connecting to backend at http://127.0.0.1:8000");
    return "http://127.0.0.1:8000";
  }

  if (protocol === "file:") {
    console.log("ℹ️ Running from file protocol, connecting to backend at http://127.0.0.1:8000");
    return "http://127.0.0.1:8000";
  }

  // Default: Assume backend is on same host, otherwise fallback to 8000
  console.warn(`⚠️ Unusual host '${host}'. Trying current origin first, fallback to http://127.0.0.1:8000`);
  return origin || "http://127.0.0.1:8000";
}

async function fetchApi(path, options) {
  let response = await fetch(`${API_BASE}${path}`, options);

  // If the page is on port 5500 and the first request hits the static file server,
  // retry the request against the backend on port 8000.
  if (!response.ok && API_BASE.includes(":5500")) {
    console.warn("⚠️ Primary API call failed on port 5500, retrying on port 8000");
    response = await fetch(`http://127.0.0.1:8000${path}`, options);
  }

  return response;
}

function countWords(text) {
  return String(text || "").trim().split(/\s+/).filter(Boolean).length;
}

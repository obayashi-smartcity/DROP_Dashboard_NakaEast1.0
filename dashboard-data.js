(() => {
  const DATA_URL = "json/nakanoshima_dashboard.json";
  const timestampFormat = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  function parseTimestamp(value) {
    const normalized = value.includes("T") ? value : value.replace(" ", "T");
    return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(normalized) ? normalized : `${normalized}+09:00`);
  }

  async function load() {
    const response = await fetch(DATA_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function updateLatestTimestamp(data) {
    const value = data.meta?.latest_timestamp;
    const timestamp = document.getElementById("latest-timestamp");
    const status = document.getElementById("data-status");
    timestamp.textContent = value ? formatTimestamp(value) : "—";
    if (value) timestamp.dateTime = parseTimestamp(value).toISOString();
    status.classList.toggle("is-ready", Boolean(value));
  }

  function formatTimestamp(value) {
    return timestampFormat.format(parseTimestamp(value));
  }

  function showError() {
    const timestamp = document.getElementById("latest-timestamp");
    const status = document.getElementById("data-status");
    timestamp.textContent = "取得失敗";
    timestamp.removeAttribute("datetime");
    status.classList.add("is-error");
  }

  window.DashboardData = { load, updateLatestTimestamp, formatTimestamp, showError };
})();
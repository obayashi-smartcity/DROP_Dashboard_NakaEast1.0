const DATA_URL = "json/nakanoshima_dashboard.json";
const TOKYO_TIME_ZONE = "Asia/Tokyo";

const elements = {
  status: document.getElementById("data-status"),
  period: document.getElementById("period"),
  registrationCount: document.getElementById("registration-count"),
  dropCount: document.getElementById("drop-count"),
  updatedAt: document.getElementById("updated-at"),
  footerUpdated: document.getElementById("footer-updated"),
  chart: document.getElementById("registration-chart"),
  daily: document.getElementById("daily-registrations"),
  posts: document.getElementById("post-list"),
  postCountNote: document.getElementById("post-count-note"),
  message: document.getElementById("load-message"),
};

const numberFormat = new Intl.NumberFormat("ja-JP");
const dateFormat = new Intl.DateTimeFormat("ja-JP", {
  timeZone: TOKYO_TIME_ZONE,
  year: "numeric",
  month: "short",
  day: "numeric",
  weekday: "short",
});
const dateTimeFormat = new Intl.DateTimeFormat("ja-JP", {
  timeZone: TOKYO_TIME_ZONE,
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function parseLocalDateTime(value) {
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(normalized) ? normalized : `${normalized}+09:00`);
}

function formatDate(value) {
  return dateFormat.format(new Date(`${value}T00:00:00+09:00`));
}

function appendEmptyState(container, message) {
  const empty = document.createElement("p");
  empty.className = "empty-state";
  empty.textContent = message;
  container.replaceChildren(empty);
}

function makeDateRange(start, end) {
  const dates = [];
  const current = new Date(`${start}T00:00:00Z`);
  const last = new Date(`${end}T00:00:00Z`);
  while (current <= last && dates.length < 3660) {
    dates.push(current.toISOString().slice(0, 10));
    current.setUTCDate(current.getUTCDate() + 1);
  }
  return dates;
}

function renderChart(registrations, period) {
  const counts = new Map(registrations.map((registration) => [registration.date, registration.count]));
  const dates = makeDateRange(period.start, period.end);
  if (dates.length === 0) {
    appendEmptyState(elements.chart, "登録データはありません");
    return;
  }

  const maximum = Math.max(1, ...dates.map((date) => counts.get(date) || 0));
  const fragment = document.createDocumentFragment();
  dates.forEach((date) => {
    const count = counts.get(date) || 0;
    const day = document.createElement("div");
    day.className = "chart-day";
    day.setAttribute("aria-hidden", "true");
    day.title = `${formatDate(date)}: ${numberFormat.format(count)}人`;

    const label = document.createElement("span");
    label.className = "chart-count";
    label.textContent = count ? numberFormat.format(count) : "";

    const track = document.createElement("div");
    track.className = "chart-bar-track";
    const bar = document.createElement("span");
    bar.className = "chart-bar";
    bar.style.height = `${count ? Math.max(4, (count / maximum) * 100) : 1}%`;
    track.append(bar);

    const dateLabel = document.createElement("span");
    dateLabel.className = "chart-date";
    dateLabel.textContent = date.slice(5).replace("-", "/");
    day.append(label, track, dateLabel);
    fragment.append(day);
  });
  elements.chart.replaceChildren(fragment);
  elements.chart.setAttribute(
    "aria-label",
    `日別登録者数。${dates.length}日間、合計${numberFormat.format(registrations.reduce((sum, row) => sum + row.count, 0))}人`,
  );
}

function renderDailyRegistrations(registrations) {
  if (registrations.length === 0) {
    appendEmptyState(elements.daily, "登録データはありません");
    return;
  }

  const fragment = document.createDocumentFragment();
  [...registrations].reverse().forEach((registration) => {
    const row = document.createElement("div");
    row.className = "daily-row";
    const date = document.createElement("time");
    date.className = "daily-date";
    date.dateTime = registration.date;
    date.textContent = formatDate(registration.date);
    const names = document.createElement("span");
    names.className = "daily-names";
    names.textContent = registration.nicknames.join("、");
    const count = document.createElement("span");
    count.className = "daily-count";
    count.textContent = numberFormat.format(registration.count);
    row.append(date, names, count);
    fragment.append(row);
  });
  elements.daily.replaceChildren(fragment);
}

function renderPosts(posts) {
  elements.postCountNote.textContent = `${numberFormat.format(posts.length)}件`;
  if (posts.length === 0) {
    appendEmptyState(elements.posts, "対象期間の投稿はありません");
    return;
  }

  const fragment = document.createDocumentFragment();
  [...posts].reverse().forEach((post) => {
    const article = document.createElement("article");
    article.className = "post";
    const meta = document.createElement("div");
    meta.className = "post-meta";
    const time = document.createElement("time");
    time.className = "post-time";
    const postedAt = parseLocalDateTime(post.posted_at);
    time.dateTime = postedAt.toISOString();
    time.textContent = dateTimeFormat.format(postedAt);
    const nickname = document.createElement("span");
    nickname.className = "post-nickname";
    nickname.textContent = post.nickname;
    const body = document.createElement("p");
    body.className = "post-body";
    body.textContent = post.sentence;
    meta.append(time, nickname);
    article.append(meta, body);
    fragment.append(article);
  });
  elements.posts.replaceChildren(fragment);
}

function showFailure(error) {
  elements.status.classList.add("is-error");
  elements.status.lastElementChild.textContent = "データを読み込めません";
  elements.message.hidden = false;
  elements.message.textContent = `表示用データの読み込みに失敗しました。${error.message}`;
}

async function loadDashboard() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!data.meta?.period || !data.summary || !Array.isArray(data.registrations) || !Array.isArray(data.drops)) {
      throw new Error("JSONの形式が想定と異なります");
    }

    elements.registrationCount.textContent = numberFormat.format(data.summary.registration_count);
    elements.dropCount.textContent = numberFormat.format(data.summary.drop_count);
    elements.period.textContent = `${formatDate(data.meta.period.start)} 〜 ${formatDate(data.meta.period.end)}`;
    const updatedAt = dateTimeFormat.format(new Date(data.meta.generated_at));
    elements.updatedAt.textContent = updatedAt;
    elements.footerUpdated.textContent = updatedAt;
    elements.status.classList.add("is-ready");
    elements.status.lastElementChild.textContent = "データ更新済み";
    renderChart(data.registrations, data.meta.period);
    renderDailyRegistrations(data.registrations);
    renderPosts(data.drops);
  } catch (error) {
    showFailure(error);
  }
}

loadDashboard();
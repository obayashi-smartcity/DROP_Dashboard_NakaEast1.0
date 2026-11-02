const dropElements = {
  period: document.getElementById("period"),
  count: document.getElementById("drop-count"),
  mappedCount: document.getElementById("mapped-count"),
  map: document.getElementById("post-map"),
  mapNote: document.getElementById("map-note"),
  list: document.getElementById("drop-list"),
  listCount: document.getElementById("drop-list-count"),
  generatedAt: document.getElementById("generated-at"),
  message: document.getElementById("load-message"),
};

const dropNumberFormat = new Intl.NumberFormat("ja-JP");
const dropDateFormat = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  year: "numeric",
  month: "short",
  day: "numeric",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function timestampDate(value) {
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(normalized) ? normalized : `${normalized}+09:00`);
}

function popupContent(post) {
  const content = document.createElement("div");
  content.className = "map-popup";
  const name = document.createElement("strong");
  name.textContent = post.nickname || "ニックネームなし";
  const time = document.createElement("time");
  time.dateTime = timestampDate(post.posted_at).toISOString();
  time.textContent = dropDateFormat.format(timestampDate(post.posted_at));
  const sentence = document.createElement("p");
  sentence.textContent = post.sentence || "本文なし";
  content.append(name, time, sentence);
  return content;
}

function renderDropList(posts, mapState) {
  dropElements.listCount.textContent = `${dropNumberFormat.format(posts.length)}件`;
  if (!posts.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "対象期間の投稿はありません";
    dropElements.list.replaceChildren(empty);
    return;
  }

  const fragment = document.createDocumentFragment();
  [...posts].sort((left, right) => right.posted_at.localeCompare(left.posted_at)).forEach((post) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "drop-row";
    row.title = "地図で投稿地点を表示";
    const meta = document.createElement("span");
    meta.className = "drop-meta";
    const time = document.createElement("time");
    time.dateTime = timestampDate(post.posted_at).toISOString();
    time.textContent = dropDateFormat.format(timestampDate(post.posted_at));
    const nickname = document.createElement("strong");
    nickname.textContent = post.nickname || "ニックネームなし";
    meta.append(time, nickname);
    const sentence = document.createElement("span");
    sentence.className = "drop-sentence";
    sentence.textContent = post.sentence || "本文なし";
    row.append(meta, sentence);
    row.addEventListener("click", () => {
      const marker = mapState.markers.get(post);
      if (marker && mapState.map) {
        mapState.map.flyTo(marker.getLatLng(), Math.max(mapState.map.getZoom(), 16), { duration: 0.35 });
        marker.openPopup();
      }
    });
    fragment.append(row);
  });
  dropElements.list.replaceChildren(fragment);
}

function initializeMap(posts) {
  if (typeof L === "undefined") {
    dropElements.mapNote.textContent = "地図ライブラリを読み込めませんでした";
    return { map: null, markers: new Map() };
  }

  const settings = window.DASHBOARD_CONFIG?.map || {};
  const map = L.map(dropElements.map, { zoomControl: true, scrollWheelZoom: false })
    .setView(settings.center || [34.6905, 135.5023], settings.zoom || 14);
  const tile = settings.tile || "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
  const key = settings.cartoApiKey;
  const tileUrl = key ? `${tile}?key=${encodeURIComponent(key)}` : tile;
  L.tileLayer(tileUrl, { attribution: settings.attribution || "© OpenStreetMap © CARTO", maxZoom: 19 }).addTo(map);

  const markers = new Map();
  const points = [];
  posts.forEach((post) => {
    const latitude = Number(post.latitude);
    const longitude = Number(post.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < 20 || latitude > 46 || longitude < 122 || longitude > 154) return;
    const marker = L.circleMarker([latitude, longitude], {
      radius: 7,
      color: "#ffffff",
      weight: 2,
      fillColor: "#c45b42",
      fillOpacity: 0.95,
    }).bindPopup(popupContent(post), { maxWidth: 280 });
    marker.addTo(map);
    markers.set(post, marker);
    points.push([latitude, longitude]);
  });

  if (points.length) map.fitBounds(points, { padding: [26, 26], maxZoom: 17 });
  requestAnimationFrame(() => map.invalidateSize());
  dropElements.mapNote.textContent = points.length
    ? `${dropNumberFormat.format(points.length)}件の投稿地点`
    : "位置情報のある投稿はありません";
  return { map, markers };
}

async function loadDropsPage() {
  try {
    const data = await window.DashboardData.load();
    if (!Array.isArray(data.drops) || !data.meta?.period || !data.summary) {
      throw new Error("JSONの形式が想定と異なります");
    }
    const posts = data.drops;
    dropElements.count.textContent = dropNumberFormat.format(data.summary.drop_count);
    dropElements.period.textContent = `${dropDateFormat.format(new Date(`${data.meta.period.start}T00:00:00+09:00`))} 〜 ${dropDateFormat.format(new Date(`${data.meta.period.end}T23:59:59+09:00`))}`;
    dropElements.generatedAt.textContent = window.DashboardData.formatTimestamp(data.meta.generated_at);
    window.DashboardData.updateLatestTimestamp(data);
    const mapState = initializeMap(posts);
    dropElements.mappedCount.textContent = dropNumberFormat.format(mapState.markers.size);
    renderDropList(posts, mapState);
  } catch (error) {
    window.DashboardData.showError();
    dropElements.message.hidden = false;
    dropElements.message.textContent = `投稿データを読み込めませんでした。${error.message}`;
    dropElements.mappedCount.textContent = "0";
    renderDropList([], { map: null, markers: new Map() });
    dropElements.mapNote.textContent = "投稿データを読み込めませんでした";
  }
}

loadDropsPage();
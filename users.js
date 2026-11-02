const userElements = {
  period: document.getElementById("period"),
  count: document.getElementById("user-count"),
  days: document.getElementById("registration-days"),
  list: document.getElementById("user-list"),
  listCount: document.getElementById("user-list-count"),
  generatedAt: document.getElementById("generated-at"),
  message: document.getElementById("load-message"),
};

const userNumberFormat = new Intl.NumberFormat("ja-JP");
const userDateFormat = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  year: "numeric",
  month: "short",
  day: "numeric",
  weekday: "short",
});

function renderUsers(users) {
  userElements.listCount.textContent = `${userNumberFormat.format(users.length)}人`;
  if (!users.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "対象期間の登録ユーザーはいません";
    userElements.list.replaceChildren(empty);
    return;
  }

  const fragment = document.createDocumentFragment();
  [...users].sort((left, right) => right.created_at.localeCompare(left.created_at)).forEach((user) => {
    const row = document.createElement("div");
    row.className = "user-row";
    const time = document.createElement("time");
    time.className = "user-time";
    time.dateTime = user.created_at.replace(" ", "T");
    time.textContent = userDateFormat.format(new Date(`${user.created_at.replace(" ", "T")}+09:00`));
    const nickname = document.createElement("span");
    nickname.className = "user-nickname";
    nickname.textContent = user.nickname || "ニックネームなし";
    row.append(time, nickname);
    fragment.append(row);
  });
  userElements.list.replaceChildren(fragment);
}

async function loadUsersPage() {
  try {
    const data = await window.DashboardData.load();
    if (!Array.isArray(data.users) || !data.meta?.period || !data.summary) {
      throw new Error("JSONの形式が想定と異なります");
    }
    const users = data.users;
    userElements.count.textContent = userNumberFormat.format(data.summary.registration_count);
    userElements.days.textContent = userNumberFormat.format(data.registrations.length);
    userElements.period.textContent = `${userDateFormat.format(new Date(`${data.meta.period.start}T00:00:00+09:00`))} 〜 ${userDateFormat.format(new Date(`${data.meta.period.end}T00:00:00+09:00`))}`;
    userElements.generatedAt.textContent = window.DashboardData.formatTimestamp(data.meta.generated_at);
    window.DashboardData.updateLatestTimestamp(data);
    renderUsers(users);
  } catch (error) {
    window.DashboardData.showError();
    userElements.message.hidden = false;
    userElements.message.textContent = `登録データを読み込めませんでした。${error.message}`;
    renderUsers([]);
  }
}

loadUsersPage();
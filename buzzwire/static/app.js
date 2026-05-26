const boardEl = document.querySelector("#board");
const statusEl = document.querySelector("#status");
const countsEl = document.querySelector("#board-counts");
const manualForm = document.querySelector("#manual-form");
const manualToggle = document.querySelector("#manual-toggle");
const pageFilter = document.querySelector("#page-filter");
const goodOnlyButton = document.querySelector("#good-only");
const toastStack = document.querySelector("#toast-stack");
const detailModal = document.querySelector("#detail-modal");
const detailContent = document.querySelector("#detail-content");
const settingsModal = document.querySelector("#settings-modal");
const profilePicker = document.querySelector("#profile-picker");
const profileForm = document.querySelector("#profile-form");
const copyProfileButton = document.querySelector("#copy-profile");

const columns = [
  ["fetched", "New"],
  ["scored", "Scored"],
  ["generated", "Ready"],
  ["approved", "Approved"],
  ["rejected", "Rejected"],
  ["used", "Used"],
];

const postColumns = new Set(["generated", "approved", "rejected", "used"]);

let profiles = [];
let lastBoard = null;
let selectedPage = "all";
let goodOnly = false;
let activeDetail = null;

function setStatus(message, isError = false) {
  statusEl.textContent = message || "";
  statusEl.classList.toggle("error", Boolean(isError));
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessage(data.detail) || "Request failed");
  }
  return data;
}

function errorMessage(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(errorMessage).filter(Boolean).join(" ");
  if (typeof detail === "object") {
    return [
      detail.message,
      detail.error_type,
      detail.error,
      detail.database_url ? `DB: ${detail.database_url}` : "",
      detail.hint,
    ].filter(Boolean).join(" | ");
  }
  return String(detail);
}

function asArray(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function csvToArray(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function arrayToCsv(value) {
  return asArray(value).join(", ");
}

function cleanUsername(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return text.startsWith("@") ? text : `@${text}`;
}

function copyUsername(value) {
  const base = cleanUsername(value)
    .replace(/^@/, "")
    .replace(/[^a-zA-Z0-9._]/g, "")
    .replace(/_copy\d*$/i, "");
  return base ? `@${base}_copy` : "";
}

function profileControl(name) {
  return profileForm.querySelector(`[name="${name}"]`);
}

function setProfileValue(name, value) {
  profileControl(name).value = value ?? "";
}

function normalizedScore(value) {
  const score = Number(value);
  if (!Number.isFinite(score)) return null;
  return score > 0 && score <= 1 ? score * 10 : score;
}

function scoreLabel(value) {
  const score = normalizedScore(value);
  if (score === null) return "Pending";
  return score.toFixed(1).replace(/\.0$/, "");
}

function riskClass(value) {
  const risk = String(value || "pending").toLowerCase();
  if (["low", "medium", "high"].includes(risk)) return risk;
  return "pending";
}

function allPosts(board = lastBoard) {
  if (!board) return [];
  return ["generated", "approved", "rejected", "used"].flatMap((key) => board[key] || []);
}

function findAnyPost(id) {
  const postId = Number(id);
  return allPosts().find((item) => Number(item.id) === postId) || null;
}

function findBoardItem(kind, id) {
  if (postColumns.has(kind)) return findAnyPost(id);
  const itemId = Number(id);
  return (lastBoard?.[kind] || []).find((item) => Number(item.id) === itemId) || null;
}

function showToast(title, stats = {}, isError = false) {
  const toast = document.createElement("article");
  toast.className = `toast${isError ? " error" : ""}`;
  const statRows = Object.entries(stats)
    .map(([label, value]) => `<span><strong>${esc(value)}</strong>${esc(label)}</span>`)
    .join("");
  toast.innerHTML = `
    <div class="toast-title">${esc(title)}</div>
    ${statRows ? `<div class="toast-stats">${statRows}</div>` : ""}
  `;
  toastStack.appendChild(toast);
  window.setTimeout(() => toast.classList.add("leaving"), 4200);
  window.setTimeout(() => toast.remove(), 4800);
}

function sourceErrorMessage(result) {
  const errors = result.errors || [];
  if (!errors.length) return "";
  const firstError = String(errors[0].error || "");
  if (firstError.includes("WinError 10013") || firstError.toLowerCase().includes("forbidden")) {
    return "RSS network access is blocked for the server.";
  }
  return firstError || `${errors.length} source errors.`;
}

function renderPageSelect() {
  pageFilter.innerHTML = "";
  pageFilter.append(new Option("All Pages", "all"));
  profiles.forEach((profile) => {
    const label = profile.username ? `${profile.page_name} ${profile.username}` : profile.page_name;
    pageFilter.append(new Option(label, profile.page_name));
  });
  pageFilter.append(new Option("Add New Page +", "__add__"));
  const valid = selectedPage === "all" || profiles.some((profile) => profile.page_name === selectedPage);
  if (!valid) selectedPage = "all";
  pageFilter.value = selectedPage;
}

function renderProfilePicker() {
  profilePicker.innerHTML = "";
  profiles.forEach((profile) => {
    const label = profile.username ? `${profile.page_name} ${profile.username}` : profile.page_name;
    profilePicker.append(new Option(label, String(profile.id)));
  });
}

async function loadProfiles() {
  profiles = await request("/api/profiles");
  renderPageSelect();
  renderProfilePicker();
}

function fillProfileForm(profile = null) {
  const fallback = {
    id: "",
    page_name: "",
    username: "",
    niche: "",
    audience: "",
    emotional_drivers: [],
    allowed_topics: [],
    blocked_topics: [],
    preferred_sources: [],
    country_focus: "Global",
    tone_rules: "",
    headline_style: "",
    caption_style: "",
    visual_style: "",
    risk_tolerance: "medium",
  };
  const data = profile || fallback;
  setProfileValue("id", data.id || "");
  setProfileValue("page_name", data.page_name || "");
  setProfileValue("username", data.username || "");
  setProfileValue("niche", data.niche || "");
  setProfileValue("audience", data.audience || "");
  setProfileValue("emotional_drivers", arrayToCsv(data.emotional_drivers));
  setProfileValue("allowed_topics", arrayToCsv(data.allowed_topics));
  setProfileValue("blocked_topics", arrayToCsv(data.blocked_topics));
  setProfileValue("preferred_sources", arrayToCsv(data.preferred_sources));
  setProfileValue("country_focus", data.country_focus || "");
  setProfileValue("tone_rules", data.tone_rules || "");
  setProfileValue("headline_style", data.headline_style || "");
  setProfileValue("caption_style", data.caption_style || "");
  setProfileValue("visual_style", data.visual_style || "");
  setProfileValue("risk_tolerance", data.risk_tolerance || "medium");
  if (profile?.id) profilePicker.value = String(profile.id);
}

function openSettings(newProfile = false) {
  settingsModal.hidden = false;
  if (newProfile || !profiles.length) {
    fillProfileForm(null);
  } else {
    const selected = profiles.find((profile) => String(profile.id) === profilePicker.value) || profiles[0];
    fillProfileForm(selected);
  }
}

function selectedProfile() {
  return profiles.find((profile) => String(profile.id) === profilePicker.value) || profiles[0] || null;
}

function copyCurrentSettings() {
  const base = selectedProfile();
  if (!base) {
    fillProfileForm(null);
    return;
  }
  const copy = {
    ...base,
    id: "",
    page_name: `${base.page_name} Copy`,
    username: copyUsername(base.username || base.page_name),
  };
  fillProfileForm(copy);
  showToast("Settings Copied", { From: base.page_name });
}

function closeModal(kind) {
  if (kind === "settings") settingsModal.hidden = true;
  if (kind === "detail") {
    detailModal.hidden = true;
    activeDetail = null;
  }
}

function titleForItem(kind, item) {
  return item.viral_title || item.topic_title || item.title || "Untitled story";
}

function pageForItem(kind, item) {
  if (item.page_name) return item.username ? `${item.page_name} ${item.username}` : item.page_name;
  if (kind === "fetched") return "No page yet";
  if (kind === "scored") return "Waiting for match";
  return "Unassigned";
}

function cardActions(kind, id) {
  if (!postColumns.has(kind)) {
    return `<button type="button" data-action="open" data-kind="${esc(kind)}" data-id="${esc(id)}">Open</button>`;
  }
  return `
    <button type="button" data-action="open" data-kind="${esc(kind)}" data-id="${esc(id)}">Open</button>
    <button type="button" data-action="approve" data-kind="${esc(kind)}" data-id="${esc(id)}">Approve</button>
    <button type="button" data-action="reject" data-kind="${esc(kind)}" data-id="${esc(id)}">Reject</button>
  `;
}

function compactCard(kind, item, index = 0) {
  const title = titleForItem(kind, item);
  const risk = item.risk_level || "Pending";
  const delayIndex = Math.min(index, 10);
  return `
    <article class="ticket-card" style="--card-index: ${delayIndex}" data-kind="${esc(kind)}" data-id="${esc(item.id)}" tabindex="0">
      <h3>${esc(title)}</h3>
      <p class="page-line">${esc(pageForItem(kind, item))}</p>
      <div class="score-grid">
        <span>Virality <strong>${esc(scoreLabel(item.virality_score))}</strong></span>
        <span>Confidence <strong>${esc(scoreLabel(item.confidence_score))}</strong></span>
        <span>Risk <strong class="risk ${esc(riskClass(risk))}">${esc(risk)}</strong></span>
      </div>
      <div class="quick-actions">${cardActions(kind, item.id)}</div>
    </article>
  `;
}

function filterItems(kind, items) {
  return items.filter((item) => {
    if (selectedPage !== "all" && item.page_name !== selectedPage) return false;
    if (goodOnly) {
      const virality = normalizedScore(item.virality_score);
      const confidence = normalizedScore(item.confidence_score);
      if ((virality ?? 0) < 7 || (confidence !== null && confidence < 7)) return false;
    }
    return true;
  });
}

function renderBoard() {
  if (!lastBoard) return;
  const total = columns.reduce((sum, [key]) => sum + (lastBoard[key] || []).length, 0);
  countsEl.textContent = `${total} items across ${profiles.length} pages`;

  boardEl.innerHTML = columns.map(([key, title]) => {
    const items = filterItems(key, lastBoard[key] || []);
    const cards = items.length
      ? items.map((item, index) => compactCard(key, item, index)).join("")
      : `<p class="empty">No items</p>`;
    return `
      <section class="board-column">
        <div class="column-header">
          <h2>${esc(title)}</h2>
          <span>${items.length}</span>
        </div>
        <div class="column-cards">${cards}</div>
      </section>
    `;
  }).join("");
}

async function loadBoard() {
  lastBoard = await request("/api/board");
  renderBoard();
  if (activeDetail?.kind === "post") {
    const post = findAnyPost(activeDetail.id);
    if (post) renderPostDetail(post);
  }
}

function summarizeScan(result) {
  const processed = result.processed || [result];
  const generatedIds = processed.flatMap((item) => item.generated_post_ids || []);
  const matched = processed.reduce((sum, item) => sum + (item.matches?.length || 0), 0);
  return {
    fetched: result.items_fetched ?? 1,
    matched,
    generated: generatedIds.length,
    generatedIds: new Set(generatedIds.map(Number)),
  };
}

function countHighVirality(generatedIds) {
  if (!generatedIds.size) return 0;
  return allPosts().filter((post) => {
    return generatedIds.has(Number(post.id)) && (normalizedScore(post.virality_score) || 0) >= 8;
  }).length;
}

function linkList(item) {
  const links = [];
  const sourceUrl = item.source_url || item.topic_url || item.url;
  if (sourceUrl) {
    links.push(`<a href="${esc(sourceUrl)}" target="_blank" rel="noreferrer">${esc(item.source_name || "Source URL")}</a>`);
  }
  if (item.source_feed_url) {
    links.push(`<a href="${esc(item.source_feed_url)}" target="_blank" rel="noreferrer">${esc(item.source_name || "RSS feed")}</a>`);
  }
  if (!links.length) return "<span>Manual input or source not provided</span>";
  return links.map((link) => `<span>${link}</span>`).join("");
}

function detailField(label, value) {
  if (value === null || value === undefined || value === "") return "";
  if (Array.isArray(value)) {
    if (!value.length) return "";
    return `
      <section class="detail-block">
        <h3>${esc(label)}</h3>
        <ul>${value.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      </section>
    `;
  }
  if (typeof value === "object") {
    const rows = Object.entries(value)
      .filter(([, rowValue]) => rowValue !== null && rowValue !== undefined && rowValue !== "")
      .map(([key, rowValue]) => {
        const labelText = key.replaceAll("_", " ");
        const content = Array.isArray(rowValue) ? rowValue.join(", ") : rowValue;
        return `<p><strong>${esc(labelText)}</strong>${esc(content)}</p>`;
      })
      .join("");
    if (!rows) return "";
    return `<section class="detail-block"><h3>${esc(label)}</h3>${rows}</section>`;
  }
  return `
    <section class="detail-block">
      <h3>${esc(label)}</h3>
      <p>${esc(value)}</p>
    </section>
  `;
}

function whySelected(item) {
  const suitability = item.page_suitability || {};
  const fit = suitability[item.page_name];
  const parts = [];
  if (fit !== undefined) parts.push(`${item.page_name} fit score ${scoreLabel(fit)}`);
  if (item.categories?.length) parts.push(`Categories: ${item.categories.join(", ")}`);
  if (item.emotional_triggers?.length) parts.push(`Drivers: ${item.emotional_triggers.join(", ")}`);
  if (item.country_relevance) parts.push(`Country relevance: ${item.country_relevance}`);
  return parts.join(". ") || "BuzzWire matched this to the page profile based on topic, emotion, and risk.";
}

function sourceSummary(item) {
  return item.topic_summary || item.summary || "No source summary was provided. Open the source link before approval.";
}

function sourceHeadline(item) {
  return item.topic_title || item.title || "Untitled source story";
}

function renderPostDetail(item) {
  activeDetail = { kind: "post", id: Number(item.id) };
  detailContent.innerHTML = `
    <div class="detail-header">
      <div>
        <p class="eyebrow">${esc(item.username ? `${item.page_name} ${item.username}` : item.page_name)} | ${esc(item.status || "generated")}</p>
        <h2 id="detail-title">${esc(item.viral_title)}</h2>
      </div>
      <div class="detail-score">
        <span>V ${esc(scoreLabel(item.virality_score))}</span>
        <span>C ${esc(scoreLabel(item.confidence_score))}</span>
        <span class="risk ${esc(riskClass(item.risk_level))}">${esc(item.risk_level)}</span>
        <button class="close-button" type="button" data-close-modal="detail">Close</button>
      </div>
    </div>

    <div class="detail-actions">
      <button class="primary-button" type="button" data-modal-action="approve" data-id="${esc(item.id)}">Approve</button>
      <button class="secondary-button" type="button" data-modal-action="reject" data-id="${esc(item.id)}">Reject</button>
      <button class="secondary-button" type="button" data-modal-action="used" data-id="${esc(item.id)}">Mark Used</button>
      <button class="secondary-button" type="button" data-modal-action="regenerate-title" data-id="${esc(item.id)}">Regenerate Title</button>
      <button class="secondary-button" type="button" data-modal-action="regenerate-caption" data-id="${esc(item.id)}">Regenerate Caption</button>
      <select id="modal-tone" aria-label="Tone">
        <option value="dramatic">Dramatic</option>
        <option value="balanced">Balanced</option>
        <option value="urgent">Urgent</option>
        <option value="relatable">Relatable</option>
      </select>
      <button class="secondary-button" type="button" data-modal-action="change-tone" data-id="${esc(item.id)}">Change Tone</button>
    </div>

    <section class="detail-brief">
      <div class="detail-block news-summary-block">
        <h3>Original News</h3>
        <p><strong>Headline</strong>${esc(sourceHeadline(item))}</p>
        <p><strong>Summary</strong>${esc(sourceSummary(item))}</p>
      </div>
      <section class="detail-block source-block">
        <h3>Source</h3>
        <div>${linkList(item)}</div>
      </section>
    </section>

    <div class="detail-grid">
      ${detailField("BuzzWire Angle", {
        neutral_title: item.neutral_title,
        viral_title: item.viral_title,
        aggressive_title: item.aggressive_title,
      })}
      ${detailField("Caption", item.caption)}
      ${detailField("Carousel Ideas", item.carousel_text)}
      ${detailField("Image Direction", item.visual_direction)}
      ${detailField("Image Idea System", item.image_brief)}
      ${detailField("Suggested Image Keywords", item.suggested_image_keywords)}
      ${detailField("Why AI Selected This", whySelected(item))}
      ${detailField("Related Categories", item.categories)}
      ${detailField("Risk Notes", item.risk_notes)}
    </div>
  `;
  detailModal.hidden = false;
}

function renderRawDetail(kind, item) {
  activeDetail = { kind, id: Number(item.id) };
  detailContent.innerHTML = `
    <div class="detail-header">
      <div>
        <p class="eyebrow">${kind === "fetched" ? "New story" : "Scored story"}</p>
        <h2 id="detail-title">${esc(titleForItem(kind, item))}</h2>
      </div>
      <div class="detail-score">
        <span>V ${esc(scoreLabel(item.virality_score))}</span>
        <span class="risk ${esc(riskClass(item.risk_level))}">${esc(item.risk_level || "Pending")}</span>
        <button class="close-button" type="button" data-close-modal="detail">Close</button>
      </div>
    </div>
    <section class="detail-brief">
      <div class="detail-block news-summary-block">
        <h3>Original News</h3>
        <p><strong>Headline</strong>${esc(sourceHeadline(item))}</p>
        <p><strong>Summary</strong>${esc(sourceSummary(item))}</p>
      </div>
      <section class="detail-block source-block">
        <h3>Source</h3>
        <div>${linkList(item)}</div>
      </section>
    </section>
    <div class="detail-grid">
      ${detailField("Categories", item.categories)}
      ${detailField("Emotion Hooks", item.emotional_triggers)}
      ${detailField("Page Suitability", item.page_suitability)}
    </div>
  `;
  detailModal.hidden = false;
}

function openDetail(kind, id) {
  const item = findBoardItem(kind, id);
  if (!item) return;
  if (postColumns.has(kind)) {
    renderPostDetail(item);
  } else {
    renderRawDetail(kind, item);
  }
}

async function performPostAction(action, id) {
  const endpoints = {
    approve: `/api/posts/${id}/approve`,
    reject: `/api/posts/${id}/reject`,
    used: `/api/posts/${id}/used`,
    "regenerate-title": `/api/posts/${id}/regenerate-title`,
    "regenerate-caption": `/api/posts/${id}/regenerate-caption`,
    "change-tone": `/api/posts/${id}/change-tone`,
  };
  let body = JSON.stringify({});
  if (action === "change-tone") {
    body = JSON.stringify({ tone: document.querySelector("#modal-tone")?.value || "balanced" });
  }
  setStatus("Updating...");
  await request(endpoints[action], { method: "POST", body });
  await loadBoard();
  showToast("BuzzWire Updated", { Status: action.replaceAll("-", " ") });
  setStatus("Updated.");
}

manualToggle.addEventListener("click", () => {
  manualForm.hidden = !manualForm.hidden;
  manualToggle.classList.toggle("active", !manualForm.hidden);
});

goodOnlyButton.addEventListener("click", () => {
  goodOnly = !goodOnly;
  goodOnlyButton.classList.toggle("active", goodOnly);
  goodOnlyButton.setAttribute("aria-pressed", String(goodOnly));
  renderBoard();
});

pageFilter.addEventListener("change", () => {
  if (pageFilter.value === "__add__") {
    pageFilter.value = selectedPage;
    openSettings(true);
    return;
  }
  selectedPage = pageFilter.value;
  renderBoard();
});

document.querySelector("#settings-open").addEventListener("click", () => openSettings(false));
document.querySelector("#new-profile").addEventListener("click", () => fillProfileForm(null));
copyProfileButton.addEventListener("click", copyCurrentSettings);

profilePicker.addEventListener("change", () => {
  const profile = profiles.find((item) => String(item.id) === profilePicker.value);
  fillProfileForm(profile || null);
});

document.addEventListener("click", (event) => {
  const close = event.target.closest("[data-close-modal]");
  if (close) closeModal(close.dataset.closeModal);
});

manualForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    title: document.querySelector("#topic-title").value,
    summary: document.querySelector("#topic-summary").value,
    source_url: document.querySelector("#topic-url").value,
    niche_hint: document.querySelector("#topic-niche").value,
  };
  setStatus("Generating ideas...");
  try {
    const result = await request("/api/manual-topic", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const summary = summarizeScan(result);
    await loadBoard();
    showToast("BuzzWire Scan Complete", {
      Fetched: summary.fetched,
      Matched: summary.matched,
      Generated: summary.generated,
      "High Virality": countHighVirality(summary.generatedIds),
    });
    manualForm.reset();
    manualForm.hidden = true;
    manualToggle.classList.remove("active");
    setStatus("Manual story processed.");
  } catch (error) {
    setStatus(error.message, true);
    showToast("Scan Failed", { Error: error.message }, true);
  }
});

document.querySelector("#fetch-rss").addEventListener("click", async () => {
  setStatus("Scanning sources...");
  try {
    const result = await request("/api/fetch/rss?limit_per_source=4", { method: "POST" });
    const summary = summarizeScan(result);
    await loadBoard();
    showToast("BuzzWire Scan Complete", {
      Fetched: summary.fetched,
      Matched: summary.matched,
      Generated: summary.generated,
      "High Virality": countHighVirality(summary.generatedIds),
    });
    const sourceError = sourceErrorMessage(result);
    if (!summary.fetched && sourceError) {
      showToast("RSS Fetch Blocked", {
        Sources: result.sources_checked || 0,
        Error: sourceError,
      }, true);
      setStatus(sourceError, true);
      return;
    }
    const errors = result.errors?.length ? `${result.errors.length} source errors.` : "";
    setStatus(errors || "Scan complete.");
  } catch (error) {
    setStatus(error.message, true);
    showToast("Scan Failed", { Error: error.message }, true);
  }
});

document.querySelector("#improve-board").addEventListener("click", async () => {
  setStatus("Improving ready titles...");
  try {
    const result = await request("/api/board/regenerate?limit=100", { method: "POST" });
    await loadBoard();
    showToast("Ready Titles Improved", {
      Updated: result.updated || 0,
      Errors: result.errors?.length || 0,
    }, Boolean(result.errors?.length));
    setStatus(result.errors?.length ? "Some cards could not be regenerated." : "Ready titles improved.");
  } catch (error) {
    setStatus(error.message, true);
    showToast("Improve Failed", { Error: error.message }, true);
  }
});

document.querySelector("#refresh").addEventListener("click", async () => {
  setStatus("Refreshing...");
  try {
    await loadBoard();
    setStatus("Board refreshed.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

boardEl.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (button) {
    const { action, kind, id } = button.dataset;
    if (action === "open") {
      openDetail(kind, id);
      return;
    }
    try {
      await performPostAction(action, id);
    } catch (error) {
      setStatus(error.message, true);
      showToast("Update Failed", { Error: error.message }, true);
    }
    return;
  }
  const card = event.target.closest(".ticket-card");
  if (card) openDetail(card.dataset.kind, card.dataset.id);
});

boardEl.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  const card = event.target.closest(".ticket-card");
  if (card) openDetail(card.dataset.kind, card.dataset.id);
});

detailContent.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-modal-action]");
  if (!button) return;
  try {
    await performPostAction(button.dataset.modalAction, button.dataset.id);
  } catch (error) {
    setStatus(error.message, true);
    showToast("Update Failed", { Error: error.message }, true);
  }
});

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = profileControl("id").value;
  const payload = {
    page_name: profileControl("page_name").value.trim(),
    username: cleanUsername(profileControl("username").value),
    niche: profileControl("niche").value.trim(),
    audience: profileControl("audience").value.trim(),
    emotional_drivers: csvToArray(profileControl("emotional_drivers").value),
    allowed_topics: csvToArray(profileControl("allowed_topics").value),
    blocked_topics: csvToArray(profileControl("blocked_topics").value),
    preferred_sources: csvToArray(profileControl("preferred_sources").value),
    country_focus: profileControl("country_focus").value.trim(),
    tone_rules: profileControl("tone_rules").value.trim(),
    headline_style: profileControl("headline_style").value.trim(),
    caption_style: profileControl("caption_style").value.trim(),
    visual_style: profileControl("visual_style").value.trim(),
    risk_tolerance: profileControl("risk_tolerance").value,
  };
  try {
    const path = id ? `/api/profiles/${id}` : "/api/profiles";
    const method = id ? "PUT" : "POST";
    const result = await request(path, { method, body: JSON.stringify(payload) });
    await loadProfiles();
    selectedPage = result.profile.page_name;
    renderPageSelect();
    renderBoard();
    fillProfileForm(result.profile);
    showToast("Page Saved", { Page: result.profile.page_name });
  } catch (error) {
    showToast("Save Failed", { Error: error.message }, true);
  }
});

async function boot() {
  try {
    await loadProfiles();
    await loadBoard();
    setStatus("Ready.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

boot();

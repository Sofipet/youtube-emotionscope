const API = {
  demo: "/demo",
  demoInsights: "/demo/insights",
  analyze: "/analyze",
  unlock: "/unlock",
  videoInsight: "/agent/video-insight"
};

let liveUnlocked = false;
let accessToken = "";
let currentAnalysisPayload = null;
let currentMode = "none";
let demoInsightsMap = {};

let primaryChart = null;
let valenceChart = null;
let nuancedChart = null;
let timelineChart = null;

const EMOTION_COLORS = {
  anger: "#dc8fab",
  sadness: "#6d97d8",
  trust: "#5cae98",
  disgust: "#d39d62",
  anticipation: "#a98fe8",
  fear: "#b87f6a",
  joy: "#e5b85c",
  surprise: "#79b6cf"
};

const VALENCE_COLORS = {
  positive: "#7cc6a8",
  negative: "#e29aae",
  neutral: "#a6c4ea",
  mixed: "#e7cd78"
};

const NUANCED_COLORS = {
  frustration: "#b58be8",
  skepticism: "#7fa6d9",
  helplessness: "#8fc6b0",
  moral_outrage: "#e08aa0",
  solidarity: "#6fc1a7",
  sarcasm: "#d4a66a"
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("runDemoBtn").addEventListener("click", loadDemoExample);
  document.getElementById("unlockBtn").addEventListener("click", unlockLiveMode);
  document.getElementById("runLiveBtn").addEventListener("click", runLiveAnalysis);
  document.getElementById("askVideoBtn").addEventListener("click", askAboutCurrentVideo);

  document.querySelectorAll(".demo-question").forEach((button) => {
    button.addEventListener("click", () => {
      const question = button.dataset.question || "";
      document.getElementById("videoQuestion").value = question;

      if (currentMode === "demo" && demoInsightsMap[question]) {
        renderAgentAnswer(demoInsightsMap[question]);
      }
    });
  });
});

async function loadDemoExample() {
  resetStates();
  setLoading(true);

  try {
    const [analysisResponse, insightsResponse] = await Promise.all([
      fetch(API.demo),
      fetch(API.demoInsights)
    ]);

    if (!analysisResponse.ok) throw new Error("Could not load demo example.");
    if (!insightsResponse.ok) throw new Error("Could not load demo insights.");

    const analysisData = await analysisResponse.json();
    const insightsData = await insightsResponse.json();

    currentAnalysisPayload = analysisData;
    currentMode = "demo";
    demoInsightsMap = {};

    (insightsData.items || []).forEach((item) => {
      demoInsightsMap[item.question] = item;
    });

    hideAgentCard();
    renderAnalysis(analysisData);
    updateAskButtonState();
  } catch (error) {
    showError(error.message || "Failed to load demo example.");
  } finally {
    setLoading(false);
  }
}

async function unlockLiveMode() {
  const tokenInput = document.getElementById("accessToken");
  const unlockStatus = document.getElementById("unlockStatus");
  const runLiveBtn = document.getElementById("runLiveBtn");

  unlockStatus.textContent = "";
  unlockStatus.className = "status-text";

  const token = tokenInput.value.trim();
  if (!token) {
    unlockStatus.textContent = "Please enter an access token.";
    unlockStatus.classList.add("error");
    return;
  }

  try {
    const response = await fetch(API.unlock, {
      method: "POST",
      headers: {
        "x-access-token": token
      }
    });

    if (!response.ok) throw new Error("Invalid access token.");

    const data = await response.json();
    if (data.live_mode_enabled) {
      liveUnlocked = true;
      accessToken = token;
      runLiveBtn.disabled = false;
      unlockStatus.textContent = "Live mode unlocked.";
      unlockStatus.classList.add("success");
      updateAskButtonState();
    } else {
      throw new Error("Access token was not accepted.");
    }
  } catch (error) {
    liveUnlocked = false;
    accessToken = "";
    runLiveBtn.disabled = true;
    unlockStatus.textContent = error.message || "Failed to unlock live mode.";
    unlockStatus.classList.add("error");
    updateAskButtonState();
  }
}

async function runLiveAnalysis() {
  const videoUrl = document.getElementById("videoUrl").value.trim();

  if (!liveUnlocked) {
    showError("Please unlock live mode first.");
    return;
  }

  if (!videoUrl) {
    showError("Please paste a YouTube video URL.");
    return;
  }

  resetStates();
  setLoading(true);

  try {
    const response = await fetch(API.analyze, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-access-token": accessToken
      },
      body: JSON.stringify({ video_url: videoUrl })
    });

    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Failed to run live analysis.");

    currentAnalysisPayload = body;
    currentMode = "live";
    demoInsightsMap = {};
    hideAgentCard();
    renderAnalysis(body);
    updateAskButtonState();
  } catch (error) {
    showError(error.message || "Failed to run live analysis.");
  } finally {
    setLoading(false);
  }
}

async function askAboutCurrentVideo() {
  const question = document.getElementById("videoQuestion").value.trim();

  if (!currentAnalysisPayload) {
    showError("Analyze or load a video first.");
    return;
  }

  if (!question) {
    showError("Please enter a question about the current video.");
    return;
  }

  if (!liveUnlocked) {
    showError("Please unlock live mode first.");
    return;
  }

  resetStates();
  setLoading(true);

  try {
    const response = await fetch(API.videoInsight, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-access-token": accessToken
      },
      body: JSON.stringify({
        analysis: currentAnalysisPayload,
        question
      })
    });

    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Failed to get video insight.");

    renderAgentAnswer(body);
  } catch (error) {
    showError(error.message || "Failed to get video insight.");
  } finally {
    setLoading(false);
  }
}

function updateAskButtonState() {
  const askBtn = document.getElementById("askVideoBtn");
  askBtn.disabled = !currentAnalysisPayload || !liveUnlocked;
}

function renderAgentAnswer(data) {
  const card = document.getElementById("agentResultsCard");
  const chatEl = document.getElementById("agentChat");
  const followupsEl = document.getElementById("agentFollowups");
  const currentQuestion = document.getElementById("videoQuestion").value.trim();

  chatEl.innerHTML = "";
  followupsEl.innerHTML = "";

  if (currentQuestion) {
    const userBubble = document.createElement("div");
    userBubble.className = "agent-bubble user";
    userBubble.innerHTML = `
      <span class="agent-bubble-label">You</span>
      ${escapeHtml(currentQuestion)}
    `;
    chatEl.appendChild(userBubble);
  }

  const assistantBubble = document.createElement("div");
  assistantBubble.className = "agent-bubble assistant";
  assistantBubble.innerHTML = `
      <span class="agent-bubble-label">Insight agent</span>
      ${escapeHtml(data.answer || "")}
    `;
  chatEl.appendChild(assistantBubble);

  (data.suggested_followups || []).forEach((item) => {
    const btn = document.createElement("button");
    btn.className = "btn btn-secondary followup-btn";
    btn.type = "button";
    btn.textContent = item;
    btn.addEventListener("click", () => {
      document.getElementById("videoQuestion").value = item;
    });
    followupsEl.appendChild(btn);
  });

  card.classList.remove("hidden");
}

function hideAgentCard() {
  document.getElementById("agentResultsCard").classList.add("hidden");
  document.getElementById("agentChat").innerHTML = "";
  document.getElementById("agentFollowups").innerHTML = "";
}

function renderAnalysis(data) {
  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("resultsRoot").classList.remove("hidden");

  renderVideoHeader(data.video);
  renderDescription(data.description);
  renderWarnings(data.warnings || []);
  renderComments(data.representative_comments || []);
  renderPrimaryChart(data.top_primary_emotions || []);
  renderNuancedChart(data.top_nuanced_emotions || []);
  renderValenceChart(data.valence || {});
  renderTimelineChart(data.timeline || [], data.top_primary_emotions || []);
}

function renderVideoHeader(video) {
  let title = video.title || "Untitled video";
  title = title.replace(/\s*\|\s*BBC News\s*$/i, "");
  document.getElementById("videoTitle").textContent = title;
  document.getElementById("channelName").textContent = video.channel_title || "Unknown channel";
  document.getElementById("publishedAt").textContent = formatDate(video.published_at);
  document.getElementById("commentsFetched").textContent = formatNumber(video.comments_fetched || 0);
  document.getElementById("commentsAnalyzed").textContent = formatNumber(video.comments_analyzed || 0);

  const languageChips = document.getElementById("languageChips");
  languageChips.innerHTML = "";

  (video.languages || []).forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "meta-chip language-chip";
    chip.textContent = `${item.language_label} ${Math.round(item.share * 100)}%`;
    languageChips.appendChild(chip);
  });
}

function renderDescription(description) {
  document.getElementById("descriptionText").textContent = description || "No description available.";
}

function renderWarnings(warnings) {
  const warningsCard = document.getElementById("warningsCard");
  const warningsList = document.getElementById("warningsList");
  warningsList.innerHTML = "";

  if (!warnings || warnings.length === 0) {
    warningsCard.classList.add("hidden");
    return;
  }

  warningsCard.classList.remove("hidden");

  warnings.forEach((warning) => {
    const pill = document.createElement("div");
    pill.className = "warning-pill";
    pill.textContent = humanizeLabel(warning);
    warningsList.appendChild(pill);
  });
}

function renderComments(comments) {
  const container = document.getElementById("representativeCommentsList");
  container.innerHTML = "";

  comments.forEach((comment) => {
    const card = document.createElement("div");
    card.className = "comment-card";

    const top = document.createElement("div");
    top.className = "comment-top";

    top.appendChild(makeEmotionTag(comment.primary_emotion));

    if (comment.nuanced_emotion) {
      top.appendChild(makeNuancedTag(comment.nuanced_emotion));
    }

    top.appendChild(makeValenceTag(comment.valence));
    top.appendChild(makeNeutralTag(`Intensity ${formatDecimal(comment.emotion_intensity)}`));

    if (typeof comment.like_count === "number") {
      top.appendChild(makeNeutralTag(`${formatNumber(comment.like_count)} likes`));
    }

    const text = document.createElement("p");
    text.className = "comment-text";
    text.textContent = comment.text || "";

    card.appendChild(top);
    card.appendChild(text);
    container.appendChild(card);
  });
}

function makeEmotionTag(emotion) {
  const tag = document.createElement("span");
  tag.className = "comment-tag";
  tag.textContent = humanizeLabel(emotion);
  tag.style.background = hexToSoftRgba(EMOTION_COLORS[emotion] || "#d9cdf7", 0.18);
  tag.style.color = EMOTION_COLORS[emotion] || "#5d5180";
  return tag;
}

function makeNuancedTag(nuancedEmotion) {
  const tag = document.createElement("span");
  tag.className = "comment-tag";
  tag.textContent = humanizeLabel(nuancedEmotion);

  const key = normalizeNuancedKey(nuancedEmotion);
  const color = NUANCED_COLORS[key] || "#9b8bc9";

  tag.style.background = hexToSoftRgba(color, 0.18);
  tag.style.color = color;
  return tag;
}

function makeValenceTag(valence) {
  const tag = document.createElement("span");
  tag.className = "comment-tag";
  tag.textContent = humanizeLabel(valence);
  tag.style.background = hexToSoftRgba(VALENCE_COLORS[valence] || "#d8e9fb", 0.18);
  tag.style.color = VALENCE_COLORS[valence] || "#5877a4";
  return tag;
}

function makeNeutralTag(text) {
  const tag = document.createElement("span");
  tag.className = "comment-tag";
  tag.textContent = text;
  tag.style.background = "#f3effc";
  tag.style.color = "#5d5180";
  return tag;
}

function renderPrimaryChart(items) {
  const ctx = document.getElementById("primaryEmotionsChart").getContext("2d");
  destroyChart(primaryChart);

  primaryChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: items.map((x) => humanizeLabel(x.emotion)),
      datasets: [{
        data: items.map((x) => x.prevalence),
        backgroundColor: items.map((x) => EMOTION_COLORS[x.emotion] || "#a98fe8"),
        borderColor: items.map((x) => EMOTION_COLORS[x.emotion] || "#a98fe8"),
        borderWidth: 1
      }]
    },
    options: baseChartOptions({
      indexAxis: "y",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const item = items[context.dataIndex];
              return [
                `Prevalence: ${formatPercent(item.prevalence)}`,
                `Avg intensity: ${formatDecimal(item.avg_intensity)}`
              ];
            }
          }
        }
      },
      scales: {
        x: {
          min: 0,
          max: 1,
          ticks: { callback: (value) => `${Math.round(value * 100)}%` },
          grid: { color: "#eee9f6" }
        },
        y: { grid: { display: false } }
      }
    })
  });
}

function renderNuancedChart(items) {
  const ctx = document.getElementById("nuancedEmotionsChart").getContext("2d");
  destroyChart(nuancedChart);

  nuancedChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: items.map((x) => humanizeLabel(x.emotion)),
      datasets: [{
        data: items.map((x) => x.prevalence),
        backgroundColor: items.map((x) => {
          const key = normalizeNuancedKey(x.emotion);
          return NUANCED_COLORS[key] || "#a98fe8";
        }),
        borderColor: items.map((x) => {
          const key = normalizeNuancedKey(x.emotion);
          return NUANCED_COLORS[key] || "#a98fe8";
        }),
        borderWidth: 1
      }]
    },
    options: baseChartOptions({
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const item = items[context.dataIndex];
              return [
                `Prevalence: ${formatPercent(item.prevalence)}`,
                `Avg intensity: ${formatDecimal(item.avg_intensity)}`
              ];
            }
          }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 1,
          ticks: { callback: (value) => `${Math.round(value * 100)}%` },
          grid: { color: "#eee9f6" }
        },
        x: { grid: { display: false } }
      }
    })
  });
}

function renderValenceChart(valence) {
  const ctx = document.getElementById("valenceChart").getContext("2d");
  destroyChart(valenceChart);

  const labels = ["positive", "negative", "mixed", "neutral"];
  const values = labels.map((key) => valence[key] || 0);

  valenceChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels.map(humanizeLabel),
      datasets: [{
        data: values,
        backgroundColor: labels.map((key) => VALENCE_COLORS[key]),
        borderColor: "#ffffff",
        borderWidth: 2
      }]
    },
    options: baseChartOptions({
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#5b5368",
            usePointStyle: true,
            padding: 18
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.label}: ${formatPercent(context.raw)}`;
            }
          }
        }
      }
    })
  });
}

function renderTimelineChart(timeline, topPrimary) {
  const ctx = document.getElementById("timelineChart").getContext("2d");
  destroyChart(timelineChart);

  const top3 = topPrimary.slice(0, 3).map((x) => x.emotion);
  const labels = timeline.map((point) => formatTimelineDate(point.date));

  const datasets = top3.map((emotion) => ({
    label: humanizeLabel(emotion),
    data: timeline.map((point) => {
      const found = (point.primary_emotions || []).find((item) => item.emotion === emotion);
      return found ? found.prevalence : 0;
    }),
    borderColor: EMOTION_COLORS[emotion] || "#a98fe8",
    backgroundColor: EMOTION_COLORS[emotion] || "#a98fe8",
    tension: 0.2,
    fill: false,
    pointRadius: 2,
    pointHoverRadius: 4,
    borderWidth: 1.4
  }));

  timelineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets
    },
    options: baseChartOptions({
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#5b5368",
            usePointStyle: true,
            padding: 18
          }
        },
        tooltip: {
          callbacks: {
            title: function(context) {
              return context[0]?.label || "";
            },
            label: function(context) {
              return `${context.dataset.label}: ${formatPercent(context.raw)}`;
            }
          }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 1,
          ticks: {
            callback: (value) => `${Math.round(value * 100)}%`
          },
          grid: { color: "#eee9f6" }
        },
        x: {
          grid: { display: false },
          ticks: {
            color: "#746b85",
            maxRotation: 45,
            minRotation: 0
          }
        }
      }
    })
  });
}

function baseChartOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: "#5b5368" }
      }
    },
    scales: {},
    ...extra
  };
}

function destroyChart(chart) {
  if (chart) chart.destroy();
}

function resetStates() {
  hideError();
}

function setLoading(isLoading) {
  const loading = document.getElementById("loadingState");
  loading.classList.toggle("hidden", !isLoading);
}

function showError(message) {
  const error = document.getElementById("errorState");
  error.textContent = message;
  error.classList.remove("hidden");
}

function hideError() {
  const error = document.getElementById("errorState");
  error.textContent = "";
  error.classList.add("hidden");
}

function formatDate(value) {
  if (!value) return "Unknown date";
  try {
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric"
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function formatTimelineDate(value) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric"
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatDecimal(value) {
  if (value === null || value === undefined) return "0.00";
  return Number(value).toFixed(2);
}

function formatPercent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function humanizeLabel(value) {
  if (!value) return "";
  const text = String(value).replaceAll("_", " ").replaceAll("-", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function normalizeNuancedKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
}

function hexToSoftRgba(hex, alpha) {
  const clean = hex.replace("#", "");
  const bigint = parseInt(clean, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
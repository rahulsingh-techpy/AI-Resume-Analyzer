// dashboard.js — renders the latest analysis on the applicant dashboard

document.addEventListener("DOMContentLoaded", async () => {
  const raw = sessionStorage.getItem("latestAnalysis");
  const emptyState = document.getElementById("emptyState");
  const content = document.getElementById("dashboardContent");

  document.getElementById("newUploadBtn").addEventListener("click", () => {
    window.location.href = "/#upload";
  });

  const hasHistory = await loadHistory();

  if (!raw && !hasHistory) {
    emptyState.classList.remove("d-none");
    return;
  }

  content.classList.remove("d-none");

  if (raw) {
    const data = JSON.parse(raw);
    render(data);
    document.getElementById("downloadReportBtn").addEventListener("click", () => {
      window.location.href = `/api/report/${data.id}`;
    });
  } else {
    // No fresh analysis this session, but history exists — hide the "latest result"
    // panels and just show the history table with a prompt to run a new analysis.
    document.getElementById("latestResultPanels").classList.add("d-none");
  }
});

function render(data) {
  const { parsed, scores, predictions, recommendations } = data;

  document.getElementById("applicantName").textContent = parsed.name !== "Not Found" ? parsed.name : "Applicant";
  document.getElementById("applicantMeta").textContent =
    `${parsed.email !== "Not Found" ? parsed.email : "No email detected"} · Analyzed just now`;

  // Overall score ring
  const ring = document.getElementById("overallRing");
  animateCircularProgress(ring, scores.resume_score, scoreColor(scores.resume_score));
  document.getElementById("overallScoreText").textContent = `${Math.round(scores.resume_score)}%`;
  document.getElementById("overallRatingBadge").textContent = scores.overall_rating;

  // Sub-scores
  const subScores = [
    ["ATS Compatibility", scores.ats_score],
    ["Formatting", scores.formatting_score],
    ["Readability", scores.readability_score],
    ["Experience", scores.experience_score],
    ["Education", scores.education_score],
    ["Skills", scores.skill_score],
  ];
  const subScoresRow = document.getElementById("subScoresRow");
  subScoresRow.innerHTML = subScores.map(([label, val]) => `
    <div class="col-6 col-md-4">
      <div class="d-flex justify-content-between mb-1">
        <span class="small text-muted-custom">${label}</span>
        <span class="small fw-bold">${Math.round(val)}%</span>
      </div>
      <div class="progress-glass" style="height:8px;">
        <div class="bar" style="width:${val}%; background:${scoreColor(val)};"></div>
      </div>
    </div>
  `).join("");

  // Personal Info
  const personalRows = [
    ["fa-envelope", "Email", parsed.email],
    ["fa-phone", "Phone", parsed.phone],
    ["fa-brands fa-linkedin", "LinkedIn", parsed.linkedin],
    ["fa-brands fa-github", "GitHub", parsed.github],
  ];
  document.getElementById("personalInfo").innerHTML = personalRows.map(([icon, label, val]) => `
    <div class="d-flex justify-content-between">
      <span class="text-muted-custom"><i class="fa-solid ${icon} me-2"></i>${label}</span>
      <span class="text-truncate ms-2" style="max-width:60%;">${escapeHtml(val)}</span>
    </div>
  `).join("");

  // Resume Info
  const resumeRows = [
    ["Education", parsed.education],
    ["Experience", parsed.experience_section],
    ["Projects", parsed.projects],
    ["Certifications", parsed.certifications],
    ["Languages", parsed.languages],
  ];
  document.getElementById("resumeInfo").innerHTML = resumeRows.map(([label, val]) => `
    <div>
      <div class="text-muted-custom small mb-1">${label}</div>
      <div class="small" style="max-height:70px; overflow:auto; white-space:pre-line;">${escapeHtml(val)}</div>
    </div>
  `).join("");

  // Skills
  const categories = [
    ["Programming Languages", parsed.skills.programming_languages],
    ["Frameworks", parsed.skills.frameworks],
    ["Databases", parsed.skills.databases],
    ["Cloud Technologies", parsed.skills.cloud_technologies],
    ["Development Tools", parsed.skills.development_tools],
    ["Data & ML", parsed.skills.data_ml],
    ["Soft Skills", parsed.skills.soft_skills],
  ];
  document.getElementById("skillCategories").innerHTML = categories.map(([label, items]) => `
    <div class="col-md-6 col-lg-4">
      <div class="p-3" style="background: rgba(255,255,255,0.03); border-radius: 12px;">
        <div class="small text-muted-custom mb-2 fw-semibold">${label}</div>
        ${items.length
          ? items.map(s => `<span class="skill-pill existing">${escapeHtml(s)}</span>`).join("")
          : `<span class="text-muted-custom small">None detected</span>`}
      </div>
    </div>
  `).join("");

  // Predictions
  document.getElementById("jobPredictions").innerHTML = predictions.map((p, i) => `
    <div>
      <div class="d-flex justify-content-between mb-1">
        <span>${i === 0 ? '<i class="fa-solid fa-star text-warning me-1"></i>' : ''}${escapeHtml(p.role)}</span>
        <span class="fw-bold">${p.confidence}%</span>
      </div>
      <div class="progress-glass" style="height:8px;">
        <div class="bar" style="width:${p.confidence}%;"></div>
      </div>
    </div>
  `).join("");

  // Skill gap
  document.getElementById("matchedSkillsList").innerHTML = recommendations.matched_skills.length
    ? recommendations.matched_skills.map(s => `<span class="skill-pill existing"><i class="fa-solid fa-check"></i>${escapeHtml(s)}</span>`).join("")
    : `<span class="text-muted-custom small">No direct matches found.</span>`;
  document.getElementById("missingSkillsList").innerHTML = recommendations.missing_skills.length
    ? recommendations.missing_skills.map(s => `<span class="skill-pill missing"><i class="fa-solid fa-xmark"></i>${escapeHtml(s)}</span>`).join("")
    : `<span class="text-muted-custom small">You cover all key skills for this role!</span>`;

  // Tips
  document.getElementById("resumeTipsList").innerHTML = recommendations.resume_tips.map(t => `<li>${escapeHtml(t)}</li>`).join("");
  document.getElementById("roadmapList").innerHTML = recommendations.learning_roadmap.map(t => `<li>${escapeHtml(t)}</li>`).join("");
  document.getElementById("linkedinTips").innerHTML = recommendations.linkedin_tips.map(t => `<li>${escapeHtml(t)}</li>`).join("");
  document.getElementById("githubTips").innerHTML = recommendations.github_tips.map(t => `<li>${escapeHtml(t)}</li>`).join("");
  document.getElementById("portfolioTips").innerHTML = recommendations.portfolio_suggestions.map(t => `<li>${escapeHtml(t)}</li>`).join("");

  // Courses
  document.getElementById("coursesRow").innerHTML = recommendations.recommended_courses.map(c => `
    <div class="col-md-4">
      <div class="glass-card p-3 h-100">
        <h6 class="mb-1">${escapeHtml(c.name)}</h6>
        <span class="badge-gradient mb-2 d-inline-block">${escapeHtml(c.difficulty)}</span>
        <p class="small text-muted-custom mb-1"><i class="fa-regular fa-clock me-1"></i>${escapeHtml(c.duration)}</p>
        <p class="small mb-0">${c.skills.map(escapeHtml).join(", ")}</p>
      </div>
    </div>
  `).join("");

  // Career path
  document.getElementById("careerPath").innerHTML = recommendations.career_path.map((stage, i) => `
    ${i > 0 ? '<i class="fa-solid fa-arrow-right text-muted-custom"></i>' : ''}
    <span class="badge-gradient">${escapeHtml(stage)}</span>
  `).join("");

  document.getElementById("salaryEstimate").textContent = recommendations.salary_estimate;

  // Interview prep tabs
  renderInterviewTabs(recommendations.interview_prep);
}

function renderInterviewTabs(prep) {
  const tabsEl = document.getElementById("interviewTabs");
  const contentEl = document.getElementById("interviewContent");
  const categories = Object.keys(prep);

  tabsEl.innerHTML = categories.map((cat, i) => `
    <li class="nav-item">
      <button class="nav-link ${i === 0 ? "active" : ""}" style="background:${i === 0 ? "var(--glass-bg)" : "transparent"}; color:${i === 0 ? "var(--text-primary)" : "var(--text-muted)"}; border:1px solid var(--glass-border); border-radius:10px; margin-right:8px;"
        data-cat="${cat}" onclick="switchInterviewTab('${cat}')">${cat.charAt(0).toUpperCase() + cat.slice(1)}</button>
    </li>
  `).join("");

  window._interviewPrep = prep;
  switchInterviewTab(categories[0]);
}

function switchInterviewTab(cat) {
  const prep = window._interviewPrep;
  const contentEl = document.getElementById("interviewContent");
  contentEl.innerHTML = `<ul class="vstack gap-2 ps-3 mb-0">${prep[cat].map(q => `<li>${escapeHtml(q)}</li>`).join("")}</ul>`;

  document.querySelectorAll("#interviewTabs button").forEach(btn => {
    const active = btn.dataset.cat === cat;
    btn.style.background = active ? "var(--glass-bg)" : "transparent";
    btn.style.color = active ? "var(--text-primary)" : "var(--text-muted)";
  });
}

async function loadHistory() {
  const tbody = document.getElementById("historyTableBody");
  tbody.innerHTML = `<tr><td colspan="5" class="text-muted-custom">Loading...</td></tr>`;

  try {
    const res = await fetch(`/api/history`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load history.");

    if (!data.history.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-muted-custom">No previous uploads yet — analyze your first resume above.</td></tr>`;
      return false;
    }

    tbody.innerHTML = data.history.map(h => `
      <tr>
        <td>${new Date(h.upload_date).toLocaleString()}</td>
        <td>${escapeHtml(h.resume_filename)}</td>
        <td>${Math.round(h.resume_score)}%</td>
        <td>${h.predictions.length ? escapeHtml(h.predictions[0].role) : "—"}</td>
        <td class="text-end"><a href="/api/report/${h.id}" class="btn btn-sm btn-glass-outline"><i class="fa-solid fa-download"></i></a></td>
      </tr>
    `).join("");
    return true;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-muted-custom">${escapeHtml(err.message)}</td></tr>`;
    return false;
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  const div = document.createElement("div");
  div.textContent = String(str);
  return div.innerHTML;
}

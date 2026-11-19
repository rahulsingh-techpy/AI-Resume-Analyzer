// admin.js — admin dashboard: applicant table, search/filter/delete, analytics

let allApplicants = [];

document.addEventListener("DOMContentLoaded", () => {
  loadApplicants();
  loadAnalytics();

  document.getElementById("searchInput").addEventListener("input", debounce(loadApplicants, 350));
  document.getElementById("roleFilter").addEventListener("change", loadApplicants);
  document.getElementById("exportCsvBtn").addEventListener("click", () => {
    window.location.href = "/api/admin/export-csv";
  });
});

function showSection(name) {
  document.querySelectorAll(".admin-section").forEach(s => s.classList.add("d-none"));
  document.getElementById(`${name}Section`).classList.remove("d-none");
  document.querySelectorAll(".sidebar .nav-link").forEach(l => l.classList.remove("active"));
  event.target.closest(".nav-link").classList.add("active");
}

async function loadApplicants() {
  const search = document.getElementById("searchInput").value.trim();
  const role = document.getElementById("roleFilter").value;
  const tbody = document.getElementById("applicantsTableBody");
  tbody.innerHTML = `<tr><td colspan="6" class="text-muted-custom">Loading...</td></tr>`;

  try {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (role) params.set("role", role);

    const res = await fetch(`/api/admin/applicants?${params.toString()}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load applicants.");

    allApplicants = data.applicants;
    populateRoleFilter(allApplicants);

    document.getElementById("statTotal").textContent = allApplicants.length;
    const avg = allApplicants.length
      ? Math.round(allApplicants.reduce((s, a) => s + (a.resume_score || 0), 0) / allApplicants.length)
      : 0;
    document.getElementById("statAvgScore").textContent = `${avg}%`;

    if (!allApplicants.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-muted-custom">No applicants found.</td></tr>`;
      return;
    }

    tbody.innerHTML = allApplicants.map(a => {
      const topRole = a.predictions.length ? a.predictions[0].role : "—";
      return `
        <tr>
          <td>${escapeHtml(a.name)}</td>
          <td>${escapeHtml(a.email)}</td>
          <td><span class="badge-gradient">${Math.round(a.resume_score)}%</span></td>
          <td>${escapeHtml(topRole)}</td>
          <td>${new Date(a.upload_date).toLocaleDateString()}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-glass-outline me-1" onclick="viewApplicant(${a.id})"><i class="fa-solid fa-eye"></i></button>
            <button class="btn btn-sm btn-glass-outline" onclick="deleteApplicant(${a.id})"><i class="fa-solid fa-trash text-danger"></i></button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-muted-custom">${escapeHtml(err.message)}</td></tr>`;
  }
}

function populateRoleFilter(applicants) {
  const select = document.getElementById("roleFilter");
  const current = select.value;
  const roles = [...new Set(applicants.filter(a => a.predictions.length).map(a => a.predictions[0].role))];
  select.innerHTML = `<option value="">All Roles</option>` + roles.map(r => `<option value="${escapeHtml(r)}">${escapeHtml(r)}</option>`).join("");
  select.value = current;
}

async function viewApplicant(id) {
  const res = await fetch(`/api/applicant/${id}`);
  const a = await res.json();
  if (!res.ok) { showToast(a.error || "Failed to load applicant.", "error"); return; }

  const body = document.getElementById("applicantModalBody");
  body.innerHTML = `
    <h5>${escapeHtml(a.name)} <span class="badge-gradient">${Math.round(a.resume_score)}%</span></h5>
    <p class="text-muted-custom mb-3">${escapeHtml(a.email)} · ${escapeHtml(a.phone)}</p>
    <div class="row g-3 mb-3">
      ${["ats_score","formatting_score","readability_score","experience_score","education_score","skill_score"].map(key => `
        <div class="col-6 col-md-4">
          <div class="small text-muted-custom">${key.replace("_score","").replace("_"," ")}</div>
          <div class="fw-bold">${Math.round(a[key])}%</div>
        </div>
      `).join("")}
    </div>
    <h6>Predicted Roles</h6>
    <ul>${a.predictions.map(p => `<li>${escapeHtml(p.role)} — ${p.confidence}%</li>`).join("")}</ul>
    <h6>Technical Skills</h6>
    <p>${(a.skills.all_technical || []).map(escapeHtml).join(", ") || "None detected"}</p>
    <a href="/api/report/${a.id}" class="btn btn-gradient mt-2"><i class="fa-solid fa-download me-2"></i>Download Report</a>
  `;
  new bootstrap.Modal(document.getElementById("applicantModal")).show();
}

async function deleteApplicant(id) {
  if (!confirm("Delete this applicant? This cannot be undone.")) return;
  try {
    const res = await fetch(`/api/admin/applicant/${id}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to delete.");
    showToast("Applicant deleted.", "success");
    loadApplicants();
    loadAnalytics();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadAnalytics() {
  try {
    const res = await fetch("/api/admin/analytics");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load analytics.");

    document.getElementById("statTopRole").textContent =
      Object.keys(data.job_role_distribution).length
        ? Object.entries(data.job_role_distribution).sort((a, b) => b[1] - a[1])[0][0]
        : "—";
    document.getElementById("statTopSkill").textContent =
      data.top_skills.length ? data.top_skills[0][0] : "—";

    plotlyDark("chartScoreDist", {
      data: [{
        x: Object.keys(data.resume_score_distribution),
        y: Object.values(data.resume_score_distribution),
        type: "bar",
        marker: { color: ["#f87171", "#fbbf24", "#3b82f6", "#34d399"] },
      }],
      title: "Resume Score Distribution",
    });

    plotlyDark("chartRoleDist", {
      data: [{
        labels: Object.keys(data.job_role_distribution),
        values: Object.values(data.job_role_distribution),
        type: "pie",
        hole: 0.55,
        marker: { colors: ["#8b5cf6", "#3b82f6", "#22d3ee", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#60a5fa", "#2dd4bf", "#fb923c"] },
      }],
      title: "Job Role Prediction Distribution",
    });

    plotlyDark("chartTopSkills", {
      data: [{
        x: data.top_skills.map(s => s[1]),
        y: data.top_skills.map(s => s[0]),
        type: "bar",
        orientation: "h",
        marker: { color: "#8b5cf6" },
      }],
      title: "Top Skills",
      extraLayout: { margin: { l: 120 } },
    });

    plotlyDark("chartEducation", {
      data: [{
        labels: Object.keys(data.education_distribution),
        values: Object.values(data.education_distribution),
        type: "pie",
        marker: { colors: ["#8b5cf6", "#3b82f6", "#22d3ee", "#fbbf24"] },
      }],
      title: "Education Distribution",
    });

    plotlyDark("chartExperience", {
      data: [{
        x: Object.keys(data.experience_distribution),
        y: Object.values(data.experience_distribution),
        type: "bar",
        marker: { color: "#3b82f6" },
      }],
      title: "Experience Distribution",
    });

    plotlyDark("chartMonthly", {
      data: [{
        x: Object.keys(data.monthly_users),
        y: Object.values(data.monthly_users),
        type: "scatter",
        mode: "lines+markers",
        line: { color: "#22d3ee", width: 3 },
        marker: { size: 8 },
      }],
      title: "Monthly Users / Applications",
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

function plotlyDark(elId, { data, title, extraLayout = {} }) {
  const layout = {
    title: { text: title, font: { color: "#f4f4f8", family: "Inter" } },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#9498ad" },
    margin: { t: 50, l: 50, r: 20, b: 50 },
    showlegend: data[0].type === "pie",
    legend: { font: { color: "#9498ad" } },
    ...extraLayout,
  };
  Plotly.newPlot(elId, data, layout, { responsive: true, displayModeBar: false });
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  const div = document.createElement("div");
  div.textContent = String(str);
  return div.innerHTML;
}

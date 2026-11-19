// main.js — shared behaviors across all pages

document.addEventListener("DOMContentLoaded", () => {
  // Theme toggle (visual only — dark theme is the design baseline)
  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      document.body.classList.toggle("light-preview");
      const icon = themeToggle.querySelector("i");
      icon.classList.toggle("fa-moon");
      icon.classList.toggle("fa-sun");
      showToast("Theme preference saved (dark mode is recommended for this UI).");
    });
  }

  // Reveal-on-scroll for fade-in-up elements
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = 1;
        entry.target.style.transform = "translateY(0)";
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll(".feature-card, .glass-card").forEach((el) => {
    observer.observe(el);
  });
});

// Simple Bootstrap-toast-based notification helper used across pages
function showToast(message, type = "info") {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container position-fixed bottom-0 end-0 p-3";
    container.style.zIndex = 2000;
    document.body.appendChild(container);
  }

  const icons = { info: "fa-circle-info", success: "fa-circle-check", error: "fa-circle-exclamation" };
  const toastEl = document.createElement("div");
  toastEl.className = "toast toast-custom align-items-center border-0";
  toastEl.setAttribute("role", "alert");
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body"><i class="fa-solid ${icons[type] || icons.info} me-2"></i>${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toastEl);
  const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
  toast.show();
  toastEl.addEventListener("hidden.bs.toast", () => toastEl.remove());
}

// Animate a circular progress ring given a percentage (0-100)
function animateCircularProgress(circleEl, percent, color) {
  const radius = circleEl.r.baseVal.value;
  const circumference = 2 * Math.PI * radius;
  circleEl.style.strokeDasharray = `${circumference} ${circumference}`;
  circleEl.style.strokeDashoffset = circumference;
  circleEl.style.stroke = color;

  requestAnimationFrame(() => {
    const offset = circumference - (percent / 100) * circumference;
    circleEl.style.strokeDashoffset = offset;
  });
}

function scoreColor(score) {
  if (score >= 85) return "#34d399";
  if (score >= 70) return "#3b82f6";
  if (score >= 50) return "#fbbf24";
  return "#f87171";
}

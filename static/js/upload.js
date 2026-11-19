// upload.js — handles drag-and-drop upload + analysis on the landing page

(() => {
  const uploadZone = document.getElementById("uploadZone");
  const resumeInput = document.getElementById("resumeInput");
  const browseBtn = document.getElementById("browseBtn");
  const fileInfo = document.getElementById("fileInfo");
  const fileName = document.getElementById("fileName");
  const fileSize = document.getElementById("fileSize");
  const removeFile = document.getElementById("removeFile");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const progressWrap = document.getElementById("progressWrap");
  const progressBar = document.getElementById("progressBar");
  const progressLabel = document.getElementById("progressLabel");
  const successMsg = document.getElementById("successMsg");
  const errorMsg = document.getElementById("errorMsg");

  if (!uploadZone) return; // not on this page

  let selectedFile = null;

  browseBtn.addEventListener("click", () => resumeInput.click());
  uploadZone.addEventListener("click", (e) => {
    if (e.target === browseBtn) return;
    resumeInput.click();
  });

  ["dragenter", "dragover"].forEach((evt) =>
    uploadZone.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadZone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    uploadZone.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadZone.classList.remove("dragover");
    })
  );
  uploadZone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  resumeInput.addEventListener("change", () => {
    if (resumeInput.files[0]) handleFile(resumeInput.files[0]);
  });

  function handleFile(file) {
    if (file.type !== "application/pdf") {
      showToast("Only PDF files are supported.", "error");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      showToast("File is too large. Max size is 8MB.", "error");
      return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = `${(file.size / 1024).toFixed(1)} KB`;
    fileInfo.classList.remove("d-none");
    analyzeBtn.disabled = false;
    successMsg.classList.add("d-none");
    errorMsg.classList.add("d-none");
  }

  removeFile.addEventListener("click", () => {
    selectedFile = null;
    resumeInput.value = "";
    fileInfo.classList.add("d-none");
    analyzeBtn.disabled = true;
  });

  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    errorMsg.classList.add("d-none");
    successMsg.classList.add("d-none");
    progressWrap.classList.remove("d-none");
    analyzeBtn.disabled = true;
    progressBar.style.width = "0%";

    // Simulated progress while the real request is in flight
    let fakeProgress = 0;
    const interval = setInterval(() => {
      fakeProgress = Math.min(fakeProgress + Math.random() * 12, 90);
      progressBar.style.width = `${fakeProgress}%`;
    }, 250);

    const formData = new FormData();
    formData.append("resume", selectedFile);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await res.json();

      clearInterval(interval);
      progressBar.style.width = "100%";
      progressLabel.textContent = "Done!";

      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = "/login?next=/%23upload";
          return;
        }
        throw new Error(data.error || "Analysis failed.");
      }

      sessionStorage.setItem("latestAnalysis", JSON.stringify(data));
      successMsg.classList.remove("d-none");

      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 1200);
    } catch (err) {
      clearInterval(interval);
      progressWrap.classList.add("d-none");
      errorMsg.textContent = err.message;
      errorMsg.classList.remove("d-none");
      analyzeBtn.disabled = false;
    }
  });
})();

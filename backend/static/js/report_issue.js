/**
 * ==========================================================================
 * NagarWatch - Civic Issue Reporting Platform
 * File: static/js/report_issue.js
 * Purpose: Frontend logic for Photo upload preview, Geolocation, and AI Simulation
 * ==========================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Photo Upload Preview & Removal
  const photoInput = document.getElementById("issuePhoto");
  const dropzone = document.getElementById("photoDropzone");
  const previewContainer = document.getElementById("photoPreviewContainer");
  const previewImg = document.getElementById("photoPreviewImg");
  const removeBtn = document.getElementById("btnRemovePhoto");

  if (photoInput && previewContainer && previewImg) {
    const handleFile = (file) => {
      if (file && file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (e) => {
          previewImg.src = e.target.result;
          previewContainer.classList.add("has-image");
          if (dropzone) dropzone.style.display = "none";
          // Trigger simulated AI photo analysis
          const aiPhotoNotice = document.getElementById("aiPhotoAnalysisNotice");
          if (aiPhotoNotice) {
            aiPhotoNotice.innerHTML = `<strong>AI Image Analysis:</strong> Image features indicate outdoor infrastructure (Pothole / Road damage probability: 96%).`;
            aiPhotoNotice.style.display = "block";
          }
        };
        reader.readAsDataURL(file);
      }
    };

    photoInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0]);
      }
    });

    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        photoInput.value = "";
        previewImg.src = "";
        previewContainer.classList.remove("has-image");
        if (dropzone) dropzone.style.display = "block";
        const aiPhotoNotice = document.getElementById("aiPhotoAnalysisNotice");
        if (aiPhotoNotice) aiPhotoNotice.style.display = "none";
      });
    }

    // Drag and drop events for dropzone
    if (dropzone) {
      ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropzone.classList.add("dragover");
        });
      });
      ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropzone.classList.remove("dragover");
        });
      });
      dropzone.addEventListener("drop", (e) => {
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          photoInput.files = e.dataTransfer.files;
          handleFile(e.dataTransfer.files[0]);
        }
      });
    }
  }

  // 2. Browser Geolocation (Triggered only on user click)
  const btnLocate = document.getElementById("btnUseCurrentLocation");
  const inputLocation = document.getElementById("issueLocation");
  const inputLat = document.getElementById("issueLat");
  const inputLng = document.getElementById("issueLng");
  const geoStatus = document.getElementById("geoStatusMsg");

  if (btnLocate) {
    btnLocate.addEventListener("click", function () {
      if (!navigator.geolocation) {
        if (geoStatus) {
          geoStatus.textContent = "Geolocation is not supported by your browser.";
        }
        return;
      }

      btnLocate.disabled = true;
      btnLocate.textContent = "Detecting...";
      if (geoStatus) {
        geoStatus.textContent = "Requesting location permission...";
      }

      navigator.geolocation.getCurrentPosition(
        function (position) {
          const lat = position.coords.latitude.toFixed(6);
          const lng = position.coords.longitude.toFixed(6);
          if (inputLat) inputLat.value = lat;
          if (inputLng) inputLng.value = lng;
          if (inputLocation && !inputLocation.value) {
            inputLocation.value = "Near Coordinates: " + lat + ", " + lng;
          }
          if (geoStatus) {
            geoStatus.textContent = "Coordinates detected successfully: (" + lat + ", " + lng + ")";
            geoStatus.style.color = "var(--status-resolved)";
          }
          btnLocate.disabled = false;
          btnLocate.textContent = "Location Detected \u2713";
        },
        function (error) {
          btnLocate.disabled = false;
          btnLocate.textContent = "Use My Current Location";
          if (geoStatus) {
            geoStatus.textContent = "Location access denied or unavailable. You can enter manually.";
            geoStatus.style.color = "var(--color-text-muted)";
          }
        },
        { timeout: 10000 }
      );
    });
  }

  // 3. AI Category Simulation on Title changes
  const titleInput = document.getElementById("issueTitle");
  const aiCatSuggestion = document.getElementById("aiCategorySuggestion");
  const aiSevSuggestion = document.getElementById("aiSeveritySuggestion");

  if (titleInput && aiCatSuggestion) {
    titleInput.addEventListener("input", () => {
      const val = titleInput.value.toLowerCase();
      if (val.includes("pothole") || val.includes("road") || val.includes("footpath")) {
        aiCatSuggestion.textContent = "Roads & Footpaths (98% match)";
        if (aiSevSuggestion) aiSevSuggestion.textContent = "High (Potential vehicle hazard)";
      } else if (val.includes("light") || val.includes("lamp") || val.includes("dark")) {
        aiCatSuggestion.textContent = "Streetlights (95% match)";
        if (aiSevSuggestion) aiSevSuggestion.textContent = "Medium (Night safety risk)";
      } else if (val.includes("water") || val.includes("leak") || val.includes("pipe") || val.includes("drain")) {
        aiCatSuggestion.textContent = "Water & Drainage (97% match)";
        if (aiSevSuggestion) aiSevSuggestion.textContent = "High / Urgent (Flooding/wastage)";
      } else if (val.includes("garbage") || val.includes("waste") || val.includes("dump")) {
        aiCatSuggestion.textContent = "Garbage & Waste (94% match)";
        if (aiSevSuggestion) aiSevSuggestion.textContent = "Moderate Priority";
      } else {
        aiCatSuggestion.textContent = "General Civic Issue";
        if (aiSevSuggestion) aiSevSuggestion.textContent = "Standard Field Review";
      }
    });
  }

  // 4. Report Form Submission (Demo Client-Side Confirmation)
  const reportForm = document.getElementById("reportIssueForm");
  const formFeedback = document.getElementById("reportFormFeedback");

  if (reportForm) {
    reportForm.addEventListener("submit", (e) => {
      // Proceeding with form validation
      const title = document.getElementById("issueTitle").value.trim();
      const category = document.getElementById("issueCategory").value;
      const location = document.getElementById("issueLocation").value.trim();

      if (!title || !category || !location) {
        e.preventDefault();
        alert("Please fill in all required fields (Title, Category, and Location).");
        return;
      }

      if (!reportForm.getAttribute("action") && formFeedback) {
        e.preventDefault();
        formFeedback.innerHTML = `
          <div class="alert alert-success" role="alert">
            <div class="alert-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
            <div class="alert-content">
              <div class="alert-title">Issue Report Registered in Demo State!</div>
              <div>Your report "<strong>${title}</strong>" has been logged with ID #NW-${Math.floor(1000 + Math.random() * 9000)}. Status: <strong>Pending Review</strong>.</div>
            </div>
          </div>
        `;
        formFeedback.scrollIntoView({ behavior: "smooth", block: "start" });
        reportForm.reset();
        if (previewContainer) previewContainer.classList.remove("has-image");
        if (dropzone) dropzone.style.display = "block";
      }
    });
  }
});

/**
 * ==========================================================================
 * NagarWatch - Civic Issue Reporting Platform
 * File: static/js/moderation.js
 * Purpose: Interactive Moderation & Triage Workspace with Live State Changes
 * Note: Pure vanilla JavaScript with demo feedback for frontend development
 * ==========================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  // Check if mock reports are available
  const reports = (typeof NAGARWATCH_MOCK_REPORTS !== "undefined") ? [...NAGARWATCH_MOCK_REPORTS] : [];

  let activeReportId = reports.length > 0 ? reports[0].id : null;
  const queueContainer = document.getElementById("moderationQueueList");
  const queueCounter = document.getElementById("queueCountBadge");

  // DOM Elements for detail panel
  const elReportId = document.getElementById("modReportId");
  const elReportTitle = document.getElementById("modReportTitle");
  const elReportStatusBadge = document.getElementById("modReportStatusBadge");
  const elReportPriorityBadge = document.getElementById("modReportPriorityBadge");
  const elReportDesc = document.getElementById("modReportDesc");
  const elReportCategory = document.getElementById("modReportCategory");
  const elReportLocation = document.getElementById("modReportLocation");
  const elReportCitizen = document.getElementById("modReportCitizen");
  const elReportTime = document.getElementById("modReportTime");
  const elReportUpvotes = document.getElementById("modReportUpvotes");
  const elReportDisputes = document.getElementById("modReportDisputes");
  const elValidationTrack = document.getElementById("modValidationTrack");
  const elAiCategory = document.getElementById("modAiCategory");
  const elAiSeverity = document.getElementById("modAiSeverity");
  const elDuplicateAlert = document.getElementById("modDuplicateAlert");
  const elDuplicateText = document.getElementById("modDuplicateText");
  const elDeptSelect = document.getElementById("modDeptSelect");
  const elPrioritySelect = document.getElementById("modPrioritySelect");
  const elInternalNotes = document.getElementById("modInternalNotes");

  // Helper: Show Moderation Toast
  function showToast(message, type = "success") {
    let toast = document.getElementById("moderationToast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "moderationToast";
      toast.className = "mod-toast";
      document.body.appendChild(toast);
    }

    toast.className = `mod-toast ${type} show`;
    toast.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        ${type === 'success' 
          ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>'
          : type === 'warning'
          ? '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>'
          : '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>'}
      </svg>
      <span>${message}</span>
    `;

    setTimeout(() => {
      toast.classList.remove("show");
    }, 3800);
  }

  // Render Queue list
  function renderQueue() {
    if (!queueContainer) return;
    queueContainer.innerHTML = "";

    if (queueCounter) {
      queueCounter.textContent = `${reports.length} in Queue`;
    }

    reports.forEach((item) => {
      const li = document.createElement("li");
      li.className = `mod-queue-item ${item.id === activeReportId ? "active" : ""}`;
      li.setAttribute("data-id", item.id);

      const statusClass = 
        item.status === 'resolved' ? 'badge-success' :
        item.status === 'in-progress' ? 'badge-info' :
        item.status === 'verified' ? 'badge-primary' :
        item.status === 'rejected' ? 'badge-danger' : 'badge-warning';

      li.innerHTML = `
        <div class="mod-queue-item-header">
          <span class="table-id-badge">#NW-${item.id}</span>
          <span class="badge ${statusClass}" style="font-size: 0.7rem; padding: 0.15rem 0.45rem;">${item.status_display}</span>
        </div>
        <div class="mod-queue-item-title">${item.title}</div>
        <div class="mod-queue-item-meta">
          <span>${item.category}</span>
          <span>${item.created_at}</span>
        </div>
      `;

      li.addEventListener("click", () => {
        activeReportId = item.id;
        renderQueue();
        loadActiveReport();
      });

      queueContainer.appendChild(li);
    });
  }

  // Load Active Report Details
  function loadActiveReport() {
    const report = reports.find(r => r.id === activeReportId);
    if (!report) return;

    if (elReportId) elReportId.textContent = `#NW-${report.id}`;
    if (elReportTitle) elReportTitle.textContent = report.title;
    if (elReportDesc) elReportDesc.textContent = report.description;
    if (elReportCategory) elReportCategory.textContent = report.category;
    if (elReportLocation) elReportLocation.textContent = report.location;
    if (elReportCitizen) elReportCitizen.textContent = `${report.reported_by} (Verified Resident)`;
    if (elReportTime) elReportTime.textContent = report.created_at;

    // Badges
    if (elReportStatusBadge) {
      const statusClass = 
        report.status === 'resolved' ? 'badge-success' :
        report.status === 'in-progress' ? 'badge-info' :
        report.status === 'verified' ? 'badge-primary' :
        report.status === 'rejected' ? 'badge-danger' : 'badge-warning';
      elReportStatusBadge.className = `badge ${statusClass}`;
      elReportStatusBadge.textContent = report.status_display;
    }

    if (elReportPriorityBadge) {
      const priorityClass = 
        report.priority === 'urgent' ? 'badge-danger' :
        report.priority === 'high' ? 'badge-warning' :
        report.priority === 'medium' ? 'badge-info' : 'badge-neutral';
      elReportPriorityBadge.className = `badge ${priorityClass}`;
      elReportPriorityBadge.textContent = `${report.priority.toUpperCase()} PRIORITY`;
    }

    // Validation ratio
    const upvotes = report.confirmations_count || 0;
    const disputes = report.disputes_count || 0;
    const totalVotes = upvotes + disputes;
    const upvotePercent = totalVotes > 0 ? Math.round((upvotes / totalVotes) * 100) : 100;

    if (elReportUpvotes) elReportUpvotes.textContent = `${upvotes} Confirmations`;
    if (elReportDisputes) elReportDisputes.textContent = `${disputes} Disputes`;
    if (elValidationTrack) {
      elValidationTrack.innerHTML = `
        <div class="validation-upvotes" style="width: ${upvotePercent}%;"></div>
        <div class="validation-disputes" style="width: ${100 - upvotePercent}%;"></div>
      `;
    }

    // AI Suggestions
    if (elAiCategory && report.ai_suggestions) {
      elAiCategory.textContent = report.ai_suggestions.suggested_category;
    }
    if (elAiSeverity && report.ai_suggestions) {
      elAiSeverity.textContent = report.ai_suggestions.suggested_severity;
    }

    // Duplicate detection flag
    if (elDuplicateAlert && elDuplicateText && report.ai_suggestions) {
      if (report.ai_suggestions.duplicate_flag && report.ai_suggestions.duplicate_flag.toLowerCase().includes("duplicate")) {
        elDuplicateAlert.style.display = "flex";
        elDuplicateText.textContent = `AI Flag: ${report.ai_suggestions.duplicate_flag}`;
      } else {
        elDuplicateAlert.style.display = "none";
      }
    }

    // Set select values
    if (elPrioritySelect) {
      elPrioritySelect.value = report.priority;
    }
    if (elInternalNotes) {
      elInternalNotes.value = "";
    }
  }

  // Action Button Listeners
  const btnVerify = document.getElementById("btnModVerify");
  const btnInProgress = document.getElementById("btnModInProgress");
  const btnResolve = document.getElementById("btnModResolve");
  const btnDuplicate = document.getElementById("btnModDuplicate");
  const btnReject = document.getElementById("btnModReject");
  const btnSaveNotes = document.getElementById("btnModSaveNotes");

  if (btnVerify) {
    btnVerify.addEventListener("click", () => {
      const report = reports.find(r => r.id === activeReportId);
      if (report) {
        report.status = "verified";
        report.status_display = "Verified";
        renderQueue();
        loadActiveReport();
        showToast(`Report #NW-${report.id} verified and queued for field dispatch!`, "success");
      }
    });
  }

  if (btnInProgress) {
    btnInProgress.addEventListener("click", () => {
      const report = reports.find(r => r.id === activeReportId);
      if (report) {
        report.status = "in-progress";
        report.status_display = "In Progress";
        const dept = elDeptSelect ? elDeptSelect.options[elDeptSelect.selectedIndex].text : "Field Crew";
        renderQueue();
        loadActiveReport();
        showToast(`Report #NW-${report.id} assigned to ${dept} and marked In Progress!`, "info");
      }
    });
  }

  if (btnResolve) {
    btnResolve.addEventListener("click", () => {
      const report = reports.find(r => r.id === activeReportId);
      if (report) {
        report.status = "resolved";
        report.status_display = "Resolved";
        renderQueue();
        loadActiveReport();
        showToast(`Report #NW-${report.id} marked as Resolved! Citizen notification sent.`, "success");
      }
    });
  }

  if (btnDuplicate) {
    btnDuplicate.addEventListener("click", () => {
      const report = reports.find(r => r.id === activeReportId);
      if (report) {
        report.status = "rejected";
        report.status_display = "Duplicate Merged";
        renderQueue();
        loadActiveReport();
        showToast(`Report #NW-${report.id} merged into parent report.`, "warning");
      }
    });
  }

  if (btnReject) {
    btnReject.addEventListener("click", () => {
      const report = reports.find(r => r.id === activeReportId);
      if (report) {
        report.status = "rejected";
        report.status_display = "Rejected / Spam";
        renderQueue();
        loadActiveReport();
        showToast(`Report #NW-${report.id} marked as Rejected.`, "danger");
      }
    });
  }

  if (btnSaveNotes) {
    btnSaveNotes.addEventListener("click", () => {
      const note = elInternalNotes ? elInternalNotes.value.trim() : "";
      if (note) {
        showToast(`Internal moderation note saved to #NW-${activeReportId}.`, "success");
      } else {
        showToast("Please enter an internal note before saving.", "warning");
      }
    });
  }

  // Initial render
  if (reports.length > 0) {
    renderQueue();
    loadActiveReport();
  }
});


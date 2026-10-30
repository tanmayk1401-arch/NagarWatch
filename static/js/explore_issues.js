/**
 * ==========================================================================
 * NagarWatch - Civic Issue Reporting Platform
 * File: static/js/explore_issues.js
 * Purpose: Client-side search, filtering, and sorting over mock civic issues
 * ==========================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("searchKeyword");
  const categoryFilter = document.getElementById("filterCategory");
  const statusFilter = document.getElementById("filterStatus");
  const priorityFilter = document.getElementById("filterPriority");
  const sortSelect = document.getElementById("sortOrder");
  const clearBtn = document.getElementById("btnClearFilters");
  const gridContainer = document.getElementById("exploreGrid");
  const resultsCounter = document.getElementById("resultsCounter");

  if (!gridContainer || typeof NAGARWATCH_MOCK_REPORTS === "undefined") return;

  const renderReports = (reports) => {
    if (resultsCounter) {
      resultsCounter.textContent = `Showing ${reports.length} of ${NAGARWATCH_MOCK_REPORTS.length} demonstration reports`;
    }

    if (reports.length === 0) {
      gridContainer.innerHTML = `
        <div style="grid-column: 1 / -1;">
          <div class="empty-state">
            <div class="empty-state-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </div>
            <h3 class="empty-state-title">No Matching Civic Reports Found</h3>
            <p class="empty-state-description">No reports match your active search terms or filters. Try resetting the filters or submit a new report.</p>
            <button type="button" class="btn btn-primary btn-sm" id="btnEmptyReset">Reset Filters</button>
          </div>
        </div>
      `;
      const btnEmptyReset = document.getElementById("btnEmptyReset");
      if (btnEmptyReset) {
        btnEmptyReset.addEventListener("click", resetFilters);
      }
      return;
    }

    gridContainer.innerHTML = reports.map((report) => {
      let statusClass = "status-pending";
      if (report.status === "verified") statusClass = "status-verified";
      if (report.status === "in-progress") statusClass = "status-in-progress";
      if (report.status === "resolved") statusClass = "status-resolved";
      if (report.status === "rejected") statusClass = "status-rejected";

      let priorityClass = "priority-medium";
      if (report.priority === "urgent") priorityClass = "priority-urgent";
      if (report.priority === "high") priorityClass = "priority-high";
      if (report.priority === "low") priorityClass = "priority-low";

      return `
        <article class="report-card animate-fade-up">
          <div class="report-card-media">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <span class="report-card-category-tag">${report.category}</span>
          </div>
          <div class="report-card-body">
            <h3 class="report-card-title">${report.title}</h3>
            <div class="report-card-meta">
              <div class="report-card-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                  <circle cx="12" cy="10" r="3"></circle>
                </svg>
                <span>${report.location}</span>
              </div>
              <div class="report-card-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="18" rx="2"></rect>
                  <line x1="16" y1="2" x2="16" y2="6"></line>
                  <line x1="8" y1="2" x2="8" y2="6"></line>
                  <line x1="3" y1="10" x2="21" y2="10"></line>
                </svg>
                <span>${report.created_at}</span>
              </div>
            </div>
            <div class="report-card-badges">
              <span class="status-badge ${statusClass}">${report.status_display}</span>
              <span class="priority-badge ${priorityClass}">${report.priority}</span>
            </div>
          </div>
          <div class="report-card-footer">
            <span class="text-muted" style="font-size: 0.75rem;">ID: #NW-${report.id}</span>
            <a href="issue_detail.html?id=${report.id}" class="btn btn-sm btn-outline">
              <span>View Details</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </a>
          </div>
        </article>
      `;
    }).join("");
  };

  const applyFilters = () => {
    let results = [...NAGARWATCH_MOCK_REPORTS];

    // Search query
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    if (query) {
      results = results.filter((r) =>
        r.title.toLowerCase().includes(query) ||
        r.description.toLowerCase().includes(query) ||
        r.location.toLowerCase().includes(query)
      );
    }

    // Category Filter
    const cat = categoryFilter ? categoryFilter.value : "";
    if (cat) {
      results = results.filter((r) => r.category === cat);
    }

    // Status Filter
    const st = statusFilter ? statusFilter.value : "";
    if (st) {
      results = results.filter((r) => r.status === st);
    }

    // Priority Filter
    const pr = priorityFilter ? priorityFilter.value : "";
    if (pr) {
      results = results.filter((r) => r.priority === pr);
    }

    // Sort
    const sortVal = sortSelect ? sortSelect.value : "newest";
    if (sortVal === "priority") {
      const priorityWeights = { urgent: 4, high: 3, medium: 2, low: 1 };
      results.sort((a, b) => (priorityWeights[b.priority] || 0) - (priorityWeights[a.priority] || 0));
    } else {
      // Default: ID descending
      results.sort((a, b) => b.id - a.id);
    }

    renderReports(results);
  };

  const resetFilters = () => {
    if (searchInput) searchInput.value = "";
    if (categoryFilter) categoryFilter.value = "";
    if (statusFilter) statusFilter.value = "";
    if (priorityFilter) priorityFilter.value = "";
    if (sortSelect) sortSelect.value = "newest";
    applyFilters();
  };

  // Event Listeners
  if (searchInput) searchInput.addEventListener("input", applyFilters);
  if (categoryFilter) categoryFilter.addEventListener("change", applyFilters);
  if (statusFilter) statusFilter.addEventListener("change", applyFilters);
  if (priorityFilter) priorityFilter.addEventListener("change", applyFilters);
  if (sortSelect) sortSelect.addEventListener("change", applyFilters);
  if (clearBtn) clearBtn.addEventListener("click", resetFilters);

  // Initial render
  applyFilters();
});


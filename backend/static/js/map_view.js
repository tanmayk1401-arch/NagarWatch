/**
 * ==========================================================================
 * NagarWatch - Civic Issue Reporting Platform
 * File: static/js/map_view.js
 * Purpose: Leaflet map initialization, pin plotting, popups & filter logic
 * ==========================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  const mapElement = document.getElementById("leafletMap");
  const categoryFilter = document.getElementById("mapCategoryFilter");
  const statusFilter = document.getElementById("mapStatusFilter");
  const markerCounter = document.getElementById("mapMarkerCount");

  if (!mapElement) return;

  // Check if Leaflet (L) is loaded (requires internet/CDN)
  if (typeof L === "undefined") {
    mapElement.innerHTML = `
      <div style="padding: var(--space-8); text-align: center; color: var(--color-text-muted);">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin: 0 auto var(--space-3); color: var(--color-primary);">
          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
        </svg>
        <h3 style="color: var(--color-heading); margin-bottom: var(--space-2);">Offline Map Mode (Leaflet CDN Unavailable)</h3>
        <p style="max-width: 480px; margin: 0 auto var(--space-4); font-size: 0.9375rem;">
          The map canvas requires an active internet connection to load CARTO map tiles. All 6 mock coordinate reports are loaded in memory and ready to display when connected.
        </p>
      </div>
    `;
    return;
  }

  try {
    // 1. Initialize Map centered on City Coordinates (Default: 12.9716, 77.5946)
    const map = L.map("leafletMap", {
      center: [12.9716, 77.5946],
      zoom: 13,
      scrollWheelZoom: false
    });

    // 2. Add CARTO Positron Tile Layer
    const cartoKey = (mapElement.getAttribute("data-carto-key") || "").trim() || "YOUR_CARTO_API_KEY";
    const tileUrl = `https://basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=${encodeURIComponent(cartoKey)}`;
    L.tileLayer(tileUrl, {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank" rel="noopener noreferrer">CARTO</a>',
      maxZoom: 19,
      subdomains: "abcd"
    }).addTo(map);

    // 3. Markers Layer Group
    const markersLayer = L.layerGroup().addTo(map);

    const renderMarkers = () => {
      markersLayer.clearLayers();
      if (typeof NAGARWATCH_MOCK_REPORTS === "undefined") return;

      const selectedCat = categoryFilter ? categoryFilter.value : "";
      const selectedStatus = statusFilter ? statusFilter.value : "";

      const filteredReports = NAGARWATCH_MOCK_REPORTS.filter((r) => {
        const matchesCat = !selectedCat || r.category === selectedCat;
        const matchesStatus = !selectedStatus || r.status === selectedStatus;
        const hasCoords = typeof r.latitude === "number" && typeof r.longitude === "number";
        return matchesCat && matchesStatus && hasCoords;
      });

      if (markerCounter) {
        markerCounter.textContent = `${filteredReports.length} Active Pins Displayed`;
      }

      filteredReports.forEach((report) => {
        const marker = L.marker([report.latitude, report.longitude]);

        const popupContent = `
          <div class="map-popup-card">
            <div class="map-popup-header">
              <span class="report-card-category-tag" style="position: static; display: inline-block; padding: 2px 8px; font-size: 0.6875rem;">
                ${report.category}
              </span>
            </div>
            <div class="map-popup-title">${report.title}</div>
            <div class="map-popup-meta">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              <span>${report.location}</span>
            </div>
            <div class="map-popup-footer">
              <span class="status-badge status-${report.status}" style="font-size: 0.6875rem; padding: 2px 6px;">
                ${report.status_display}
              </span>
              <a href="issue_detail.html?id=${report.id}" class="btn btn-sm btn-outline" style="font-size: 0.75rem; padding: 2px 8px;">
                Details &rarr;
              </a>
            </div>
          </div>
        `;

        marker.bindPopup(popupContent);
        markersLayer.addLayer(marker);
      });
    };

    // Filter event listeners
    if (categoryFilter) categoryFilter.addEventListener("change", renderMarkers);
    if (statusFilter) statusFilter.addEventListener("change", renderMarkers);

    // Initial render
    renderMarkers();
  } catch (err) {
    console.warn("Leaflet map initialization skipped or failed:", err);
  }
});


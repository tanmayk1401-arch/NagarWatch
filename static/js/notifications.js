/**
 * ==========================================================================
 * NagarWatch - Civic Issue Reporting Platform
 * File: static/js/notifications.js
 * Purpose: Interactive notifications list, read/unread toggles & filter tabs
 * ==========================================================================
 */

const NAGARWATCH_SAMPLE_NOTIFICATIONS = [
  {
    id: 1,
    title: "Field Engineer Assigned",
    message: "Your reported pothole #NW-101 on MG Road has been assigned to Junior Engineer R. K. Sharma for on-site gravel patch work.",
    time: "25 minutes ago",
    unread: true,
    type: "info",
    report_id: 101
  },
  {
    id: 2,
    title: "Issue Verified by Ward Inspector",
    message: "Report #NW-102 (Broken streetlight at Sector 4 Market) has been physically verified by the electrical inspection team.",
    time: "2 hours ago",
    unread: true,
    type: "info",
    report_id: 102
  },
  {
    id: 3,
    title: "Work Order Completed & Resolved",
    message: "Report #NW-104 (Illegal garbage accumulation near Community Park) has been successfully cleared by the municipal sanitation crew.",
    time: "1 day ago",
    unread: true,
    type: "success",
    report_id: 104
  },
  {
    id: 4,
    title: "Civic Advisory Notice",
    message: "Scheduled drinking water supply maintenance in Ward 2 & Ward 4 tomorrow between 10:00 AM and 02:00 PM.",
    time: "2 days ago",
    unread: false,
    type: "warning",
    report_id: null
  },
  {
    id: 5,
    title: "Community Upvote Milestone",
    message: "20 neighboring residents have confirmed your report #NW-101, raising its civic triage priority to Urgent.",
    time: "3 days ago",
    unread: false,
    type: "info",
    report_id: 101
  }
];

document.addEventListener("DOMContentLoaded", () => {
  let notifications = [...NAGARWATCH_SAMPLE_NOTIFICATIONS];
  let currentFilter = "all";

  const container = document.getElementById("notificationsList");
  const unreadBadge = document.getElementById("unreadCountBadge");
  const btnTabAll = document.getElementById("notifTabAll");
  const btnTabUnread = document.getElementById("notifTabUnread");
  const btnMarkAll = document.getElementById("btnMarkAllRead");

  if (!container) return;

  const updateUnreadBadge = () => {
    const unreadCount = notifications.filter((n) => n.unread).length;
    if (unreadBadge) {
      unreadBadge.textContent = unreadCount;
      unreadBadge.style.display = unreadCount > 0 ? "inline-block" : "none";
    }
  };

  const renderNotifications = () => {
    updateUnreadBadge();

    const itemsToDisplay = currentFilter === "unread"
      ? notifications.filter((n) => n.unread)
      : notifications;

    if (itemsToDisplay.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            </svg>
          </div>
          <h3 class="empty-state-title">No Notifications</h3>
          <p class="empty-state-description">
            ${currentFilter === "unread" ? "You have read all your notifications!" : "You have no civic notifications at this time."}
          </p>
        </div>
      `;
      return;
    }

    container.innerHTML = itemsToDisplay.map((item) => {
      let iconSvg = "";
      if (item.type === "success") {
        iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
      } else if (item.type === "warning") {
        iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
      } else {
        iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
      }

      return `
        <article class="notification-card ${item.unread ? "is-unread" : "is-read"}" data-id="${item.id}">
          <div class="notif-icon-box notif-icon-${item.type}">
            ${iconSvg}
          </div>
          <div class="notif-content-area">
            <div class="notif-title-row">
              <h4 class="notif-title">${item.title}</h4>
              <span class="notif-time">${item.time}</span>
            </div>
            <p class="notif-body">${item.message}</p>
            <div class="notif-actions">
              ${item.report_id ? `<a href="issue_detail.html?id=${item.report_id}">View Report #NW-${item.report_id} &rarr;</a>` : ""}
              ${item.unread ? `<button type="button" class="btn-mark-read" data-id="${item.id}">Mark as read</button>` : `<span class="text-muted" style="font-size: 0.75rem;">✓ Read</span>`}
            </div>
          </div>
        </article>
      `;
    }).join("");

    // Attach click listeners to "Mark as read" buttons
    container.querySelectorAll(".btn-mark-read").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.getAttribute("data-id"));
        const target = notifications.find((n) => n.id === id);
        if (target) {
          target.unread = false;
          renderNotifications();
        }
      });
    });
  };

  // Tab switching
  if (btnTabAll && btnTabUnread) {
    btnTabAll.addEventListener("click", () => {
      currentFilter = "all";
      btnTabAll.classList.add("active");
      btnTabUnread.classList.remove("active");
      renderNotifications();
    });

    btnTabUnread.addEventListener("click", () => {
      currentFilter = "unread";
      btnTabUnread.classList.add("active");
      btnTabAll.classList.remove("active");
      renderNotifications();
    });
  }

  // Mark all as read button
  if (btnMarkAll) {
    btnMarkAll.addEventListener("click", () => {
      notifications.forEach((n) => (n.unread = false));
      renderNotifications();
    });
  }

  // Initial render
  renderNotifications();
});


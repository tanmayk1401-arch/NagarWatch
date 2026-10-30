/**
 * ==========================================================================
 * NagarWatch - Civic Issue Reporting Platform
 * File: static/js/base.js
 * Purpose: Global interactive utilities (mobile menu, dismissible alerts, etc.)
 * ==========================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Mobile Navigation Drawer Toggle & Accessibility
  const navbarToggler = document.querySelector(".navbar-toggler");
  const navbarCollapse = document.querySelector(".navbar-collapse");

  if (navbarToggler && navbarCollapse) {
    const closeNavbar = () => {
      navbarCollapse.classList.remove("is-open");
      navbarToggler.setAttribute("aria-expanded", "false");
    };

    navbarToggler.addEventListener("click", () => {
      const isOpen = navbarCollapse.classList.toggle("is-open");
      navbarToggler.setAttribute("aria-expanded", String(isOpen));
    });

    // Close mobile nav when clicking outside
    document.addEventListener("click", (event) => {
      if (
        navbarCollapse.classList.contains("is-open") &&
        !navbarCollapse.contains(event.target) &&
        !navbarToggler.contains(event.target)
      ) {
        closeNavbar();
      }
    });

    // Close mobile nav on Escape key
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && navbarCollapse.classList.contains("is-open")) {
        closeNavbar();
        navbarToggler.focus();
      }
    });

    // Close mobile nav when clicking any nav link inside the drawer
    navbarCollapse.querySelectorAll(".nav-link, .navbar-actions a").forEach((link) => {
      link.addEventListener("click", () => {
        if (navbarCollapse.classList.contains("is-open")) {
          closeNavbar();
        }
      });
    });
  }

  // 2. Dismissible Alert Component
  document.querySelectorAll(".alert-close").forEach((closeButton) => {
    closeButton.addEventListener("click", (event) => {
      const alertBox = event.target.closest(".alert");
      if (alertBox) {
        alertBox.style.transition = "opacity 0.2s ease, transform 0.2s ease";
        alertBox.style.opacity = "0";
        alertBox.style.transform = "translateY(-4px)";
        setTimeout(() => {
          alertBox.remove();
        }, 200);
      }
    });
  });

  // 3. View Mode Switcher (Demonstration for Resident vs Admin Toggle)
  document.querySelectorAll(".view-mode-toggle").forEach((toggleContainer) => {
    const buttons = toggleContainer.querySelectorAll(".view-mode-btn");
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        buttons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
      });
    });
  });
});

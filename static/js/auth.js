/**
 * ==========================================================================
 * NagarWatch - Civic Issue Reporting Platform
 * File: static/js/auth.js
 * Purpose: Client-side validation, password visibility toggles, and demo feedback
 * ==========================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  // --------------------------------------------------------------------------
  // 1. Password Visibility Toggle (Show / Hide Password)
  // --------------------------------------------------------------------------
  const passwordToggles = document.querySelectorAll(".btn-password-toggle");

  passwordToggles.forEach((toggleBtn) => {
    toggleBtn.addEventListener("click", () => {
      const targetInputId = toggleBtn.getAttribute("data-target");
      const passwordInput = document.getElementById(targetInputId);
      if (!passwordInput) return;

      const isPassword = passwordInput.getAttribute("type") === "password";
      passwordInput.setAttribute("type", isPassword ? "text" : "password");

      // Update button aria-label
      toggleBtn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");

      // Toggle Eye SVG icons
      const eyeOpen = toggleBtn.querySelector(".icon-eye");
      const eyeClosed = toggleBtn.querySelector(".icon-eye-off");
      if (eyeOpen && eyeClosed) {
        eyeOpen.style.display = isPassword ? "none" : "block";
        eyeClosed.style.display = isPassword ? "block" : "none";
      }
    });
  });

  // --------------------------------------------------------------------------
  // Helper: Field Validation UI Handlers
  // --------------------------------------------------------------------------
  const setFieldError = (inputElement, errorElement, message) => {
    inputElement.classList.add("is-invalid");
    inputElement.setAttribute("aria-invalid", "true");
    if (errorElement) {
      errorElement.textContent = message;
      errorElement.classList.add("is-visible");
    }
  };

  const clearFieldError = (inputElement, errorElement) => {
    inputElement.classList.remove("is-invalid");
    inputElement.removeAttribute("aria-invalid");
    if (errorElement) {
      errorElement.textContent = "";
      errorElement.classList.remove("is-visible");
    }
  };

  const isValidEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  // --------------------------------------------------------------------------
  // 2. Login Form Validation (Client-Side Only)
  // --------------------------------------------------------------------------
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    const identifierInput = document.getElementById("loginIdentifier");
    const identifierError = document.getElementById("loginIdentifierError");
    const passwordInput = document.getElementById("loginPassword");
    const passwordError = document.getElementById("loginPasswordError");
    const alertContainer = document.getElementById("authFeedback");

    // Clear errors on input
    if (identifierInput) {
      identifierInput.addEventListener("input", () => clearFieldError(identifierInput, identifierError));
    }
    if (passwordInput) {
      passwordInput.addEventListener("input", () => clearFieldError(passwordInput, passwordError));
    }

    loginForm.addEventListener("submit", (event) => {
      event.preventDefault();
      let isValid = true;

      // Validate Identifier
      if (!identifierInput.value.trim()) {
        setFieldError(identifierInput, identifierError, "Please enter your email or username.");
        isValid = false;
      } else {
        clearFieldError(identifierInput, identifierError);
      }

      // Validate Password
      if (!passwordInput.value) {
        setFieldError(passwordInput, passwordError, "Please enter your password.");
        isValid = false;
      } else {
        clearFieldError(passwordInput, passwordError);
      }

      if (isValid && alertContainer) {
        alertContainer.innerHTML = `
          <div class="alert alert-success" role="alert">
            <div class="alert-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
            <div class="alert-content">
              <div class="alert-title">Demo Sign In Successful</div>
              <div>Welcome! In full integration, your backend teammate will handle session authentication.</div>
            </div>
          </div>
        `;
        alertContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }

  // --------------------------------------------------------------------------
  // 3. Registration Form Validation (Client-Side Only)
  // --------------------------------------------------------------------------
  const registerForm = document.getElementById("registerForm");
  if (registerForm) {
    const nameInput = document.getElementById("regFullName");
    const nameError = document.getElementById("regFullNameError");
    const emailInput = document.getElementById("regEmail");
    const emailError = document.getElementById("regEmailError");
    const passwordInput = document.getElementById("regPassword");
    const passwordError = document.getElementById("regPasswordError");
    const confirmPasswordInput = document.getElementById("regConfirmPassword");
    const confirmPasswordError = document.getElementById("regConfirmPasswordError");
    const termsCheck = document.getElementById("regTerms");
    const termsError = document.getElementById("regTermsError");
    const alertContainer = document.getElementById("authFeedback");

    // Clear errors on input
    [
      [nameInput, nameError],
      [emailInput, emailError],
      [passwordInput, passwordError],
      [confirmPasswordInput, confirmPasswordError],
      [termsCheck, termsError]
    ].forEach(([input, err]) => {
      if (input) {
        input.addEventListener("input", () => clearFieldError(input, err));
      }
    });

    registerForm.addEventListener("submit", (event) => {
      event.preventDefault();
      let isValid = true;

      // Full Name
      if (!nameInput.value.trim()) {
        setFieldError(nameInput, nameError, "Please enter your full name.");
        isValid = false;
      } else {
        clearFieldError(nameInput, nameError);
      }

      // Email
      if (!emailInput.value.trim()) {
        setFieldError(emailInput, emailError, "Please enter your email address.");
        isValid = false;
      } else if (!isValidEmail(emailInput.value.trim())) {
        setFieldError(emailInput, emailError, "Please enter a valid email address (e.g. name@example.com).");
        isValid = false;
      } else {
        clearFieldError(emailInput, emailError);
      }

      // Password
      if (!passwordInput.value) {
        setFieldError(passwordInput, passwordError, "Please enter a password.");
        isValid = false;
      } else if (passwordInput.value.length < 6) {
        setFieldError(passwordInput, passwordError, "Password must be at least 6 characters long.");
        isValid = false;
      } else {
        clearFieldError(passwordInput, passwordError);
      }

      // Confirm Password
      if (!confirmPasswordInput.value) {
        setFieldError(confirmPasswordInput, confirmPasswordError, "Please confirm your password.");
        isValid = false;
      } else if (confirmPasswordInput.value !== passwordInput.value) {
        setFieldError(confirmPasswordInput, confirmPasswordError, "Passwords do not match. Please check again.");
        isValid = false;
      } else {
        clearFieldError(confirmPasswordInput, confirmPasswordError);
      }

      // Terms
      if (termsCheck && !termsCheck.checked) {
        setFieldError(termsCheck, termsError, "Please agree to the civic reporting guidelines.");
        isValid = false;
      } else if (termsCheck) {
        clearFieldError(termsCheck, termsError);
      }

      if (isValid && alertContainer) {
        alertContainer.innerHTML = `
          <div class="alert alert-success" role="alert">
            <div class="alert-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
            <div class="alert-content">
              <div class="alert-title">Demo Registration Completed</div>
              <div>Account validation passed! In full integration, this user profile will be created in the database.</div>
            </div>
          </div>
        `;
        alertContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }
});


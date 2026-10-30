# NagarWatch — Product Requirements Document (PRD)

## 1. Product Overview

**Product Name:** NagarWatch  
**Project:** PS 1.1  
**Product Type:** Civic issue reporting and monitoring platform  
**Team Size:** 4 members  
**Assigned Role:** Frontend Developer

### 1.1 Purpose

NagarWatch is designed to help residents report civic problems, explore reported issues, view issues on a map, and track their progress. It also provides an admin interface for reviewing reports and displaying information that may help prioritize civic issues.

Examples of civic problems include:
- Potholes and damaged roads.
- Garbage accumulation.
- Broken streetlights.
- Water leakage.
- Drainage problems.
- Other local infrastructure issues.

### 1.2 Scope of This Document

This document defines the requirements for the **frontend only**.

The frontend will use HTML, CSS, JavaScript, and Django Templates. It will use clearly labelled mock data wherever real backend data is unavailable.

Backend processing, database operations, authentication logic, and AI services are not part of this frontend assignment.

---

## 2. Goals

The frontend should:

1. Provide a clear and easy-to-use interface for residents.
2. Make reporting a civic issue straightforward.
3. Allow users to explore, search, filter, and view demonstration reports.
4. Display issue locations on an interactive map when coordinates are available.
5. Provide interfaces for tracking reports and viewing notifications.
6. Provide administrators with dashboard and moderation interfaces.
7. Present AI-related suggestions as demonstration UI only.
8. Work on desktop, tablet, and mobile screens.
9. Keep the code organized and beginner-friendly.
10. Make future backend integration possible without implementing it now.

---

## 3. Target Users

### 3.1 Residents

Residents need to:
- Report civic problems.
- Browse existing reports.
- View issue details.
- Explore report locations on a map.
- Track their own reports in the demonstration interface.
- View and interact with sample notifications.

### 3.2 Administrators

Administrators need to:
- Review summary metrics.
- Browse submitted reports.
- View report details.
- See suggested categories and priorities.
- Review possible duplicate reports.
- Access demonstration moderation controls.

The frontend does not implement real user roles, permissions, or administrative actions.

---

## 4. Technology Requirements

### 4.1 Required Technologies

- **HTML5:** Page structure.
- **CSS3:** Styling and responsive layouts.
- **JavaScript:** Browser-side interactions.
- **Django Templates:** Template inheritance and reusable page components.
- **Leaflet.js:** Interactive map interface.
- **OpenStreetMap:** Map tiles.

### 4.2 Restrictions

- Do not use React.
- Do not implement backend models, views, or URL handlers.
- Do not create or modify database schemas.
- Do not implement authentication or account creation.
- Do not implement real API requests.
- Do not connect to AI services.
- Do not expose API keys or credentials in frontend code.
- Do not invent backend endpoints, request formats, or response fields.

Use mock data to demonstrate frontend features until the relevant integrations are provided by the responsible teammates.

---

## 5. Application Pages

The application should contain **11 separate page templates**. Shared template components are allowed, but the pages must not be combined into one large HTML file.

### 5.1 Login Page

**Suggested template:** `templates/auth/login.html`

#### Requirements
- Display the NagarWatch name or logo.
- Provide an email or username field according to the agreed project requirements.
- Provide a password field.
- Include a show/hide password control.
- Validate required fields on the client side.
- Include a Login button.
- Provide a link to the registration page.
- Include a forgot-password placeholder if appropriate.
- Display clear validation messages.

#### Acceptance Criteria
- The page is responsive.
- Required fields are validated in the browser.
- The password visibility control works.
- The interface clearly indicates that real authentication is not connected.

### 5.2 Registration Page

**Suggested template:** `templates/auth/register.html`

#### Requirements
- Provide the required registration fields.
- Include password and confirm-password fields.
- Provide password visibility controls.
- Validate required fields.
- Check that both password entries match.
- Include a Register button.
- Provide a link to the login page.

#### Acceptance Criteria
- The form provides understandable validation messages.
- Password matching is checked in the browser.
- The page does not create an account or send data to a server.

### 5.3 Resident Dashboard

**Suggested template:** `templates/resident/dashboard.html`

#### Requirements
- Display a welcome section.
- Show total reports.
- Show open reports.
- Show in-progress reports.
- Show resolved reports.
- Display recent report cards.
- Provide a prominent Report an Issue action.
- Provide navigation to Explore Issues, Map, My Reports, and Notifications.

#### Acceptance Criteria
- Summary cards are visually consistent.
- Recent reports display their status and priority.
- All demonstration figures are clearly identified as mock data.
- Navigation links lead to the appropriate frontend pages.

### 5.4 Report an Issue

**Suggested template:** `templates/resident/report_issue.html`

#### Requirements
- Issue title input.
- Description field.
- Category selector.
- Photo upload control.
- Selected-image preview.
- Option to remove a selected image.
- Location input.
- Optional latitude and longitude inputs.
- Map-based location selection if feasible.
- Optional browser geolocation initiated by the user.
- Submit and Cancel buttons.
- Check Similar Reports button.
- Placeholder panels for AI-related suggestions.

Potential AI-related interface elements:
- Suggested issue category.
- Suggested severity or priority.
- Photo-analysis result.
- Possible duplicate reports.

#### Acceptance Criteria
- Required fields receive client-side validation.
- An uploaded image can be previewed and removed.
- Geolocation is requested only after the user chooses to use it.
- The user can understand which fields are required.
- Submission produces only a frontend demonstration response.
- No report is saved to a database or backend.

### 5.5 Explore Issues

**Suggested template:** `templates/resident/explore_issues.html`

#### Requirements
- Search by issue title or other available mock-data text.
- Filter by category.
- Filter by status.
- Filter by priority.
- Sort reports, such as by newest or priority.
- Clear filters.
- Display report cards.
- Provide links to issue details.
- Display loading, empty, and error states when appropriate.

#### Acceptance Criteria
- Search and filters work on the available mock data.
- Clearing filters restores the unfiltered results.
- An empty state appears when no reports match.
- The page remains usable on small screens.

### 5.6 Issue Details

**Suggested template:** `templates/resident/issue_detail.html`

#### Requirements
- Issue title.
- Full description.
- Category.
- Location.
- Photo when available.
- Submission date.
- Current status.
- Priority.
- Status timeline.
- Similar-report section.
- Placeholder for AI suggestions.
- Confirm and Dispute controls.
- View Location action.
- Back navigation.

#### Acceptance Criteria
- The page clearly presents the issue information.
- Missing optional information is handled gracefully.
- Confirm and Dispute actions show demonstration feedback only.
- No votes or report changes are saved to a backend.

### 5.7 Map View

**Suggested template:** `templates/resident/map_view.html`

#### Requirements
- Display a Leaflet map.
- Use OpenStreetMap tiles.
- Render mock report markers for records with valid coordinates.
- Show basic report information in marker popups.
- Provide a way to open the corresponding report details.
- Include search or filters if feasible.
- Explain when report coordinates are unavailable.

#### Acceptance Criteria
- The map displays when map resources and network access are available.
- Markers are based on the supplied demonstration coordinates.
- Reports without valid coordinates do not receive fabricated marker locations.
- Viewing the map does not require location permission.
- The page has a useful fallback message if the map cannot load.

### 5.8 My Reports

**Suggested template:** `templates/resident/my_reports.html`

#### Requirements
- Display sample reports associated with a demonstration resident.
- Show report title, category, date, status, and priority.
- Provide status filters where appropriate.
- Provide links to report details.
- Include a Report New Issue action.
- Display an empty state.

#### Acceptance Criteria
- Reports are displayed using consistent report cards or rows.
- Filters work on the mock data.
- The interface explains that the reports are examples.
- No real user-specific data is retrieved.

### 5.9 Notifications

**Suggested template:** `templates/resident/notifications.html`

#### Requirements
- Display sample notifications.
- Provide All and Unread filters.
- Include Mark as Read.
- Include Mark All Read.
- Link notifications to relevant demonstration reports when appropriate.
- Display an empty state.

#### Acceptance Criteria
- Filters operate on the sample notifications.
- Read/unread changes may be demonstrated locally in the browser.
- The page does not send notifications or update server-side records.
- Empty and read states are visually distinguishable.

### 5.10 Admin Dashboard

**Suggested template:** `templates/admin/dashboard.html`

#### Requirements
- Summary cards for pending, verified, in-progress, and resolved reports.
- High-priority report count.
- Recent reports.
- Category breakdown.
- Trend or summary visualization if feasible.
- Priority overview.
- Placeholder for AI-generated summaries.
- Navigation to report moderation.

#### Acceptance Criteria
- All metrics are based on clearly labelled mock data.
- Cards and charts use consistent styling.
- The layout works on desktop and mobile.
- AI-related content is presented as a placeholder or sample output, not a real AI result.

### 5.11 Admin Moderation

**Suggested template:** `templates/admin/moderation.html`

#### Requirements
- Display the selected report's details.
- Show the report photo and location when available.
- Show status and priority.
- Display sample AI category and severity suggestions.
- Display possible duplicate reports.
- Display sample community confirmation and dispute counts.
- Display report history.
- Provide demonstration controls for:
  - Verify.
  - Reject.
  - Mark as Duplicate.
  - Change Status.
  - Mark In Progress.
  - Mark Resolved.
  - View Similar Reports.
  - Save Decision.

#### Acceptance Criteria
- Report information is clearly organized.
- Moderation controls provide visible demonstration feedback.
- No report is actually verified, rejected, merged, or deleted.
- AI suggestions are not presented as authoritative decisions.
- The interface does not automatically reject reports.

---

## 6. Shared Components

The following reusable components should be considered:

| Component | Purpose |
|---|---|
| `base.html` | Shared page structure and template blocks |
| `navbar.html` | Resident or admin navigation |
| `footer.html` | Shared footer |
| `report_card.html` | Consistent report summaries |
| `status_badge.html` | Consistent status labels |
| `priority_badge.html` | Consistent priority labels |
| `alert.html` | Feedback and validation messages |
| `empty_state.html` | Helpful no-results messages |

Shared components should reduce duplication while preserving the requirement that each application page has its own HTML template.

---

## 7. Navigation Requirements

### 7.1 Resident Navigation

Provide navigation links for:
- Dashboard.
- Explore Issues.
- Report an Issue.
- Map.
- My Reports.
- Notifications.
- Profile placeholder.
- Logout interface placeholder.

### 7.2 Admin Navigation

Provide navigation links for:
- Admin Dashboard.
- Review Reports.
- Explore Issues or Map if useful.
- Profile placeholder.
- Logout interface placeholder.

### 7.3 Navigation Acceptance Criteria

- Navigation is consistent across related pages.
- The current page is visually identifiable.
- Mobile navigation is usable.
- Links point to the appropriate frontend pages where those pages exist.
- No real logout or authentication logic is implemented.

---

## 8. Mock Data Requirements

Use clearly separated sample data for:
- Civic reports.
- Categories.
- Statuses.
- Priority labels.
- Locations and coordinates.
- Notifications.
- Report timelines.
- Community confirmation/dispute counts.
- AI suggestions.
- Dashboard metrics.
- Possible duplicate reports.

### Rules
1. Clearly identify demonstration data in the UI or code comments.
2. Do not present mock metrics as real civic statistics.
3. Do not invent a backend API contract.
4. Do not assume final status names or priority values are confirmed by the backend team.
5. Keep the mock-data structure easy to replace when an agreed integration contract becomes available.
6. Do not use mock data to imply that an action was saved permanently.

---

## 9. AI-Related UI Requirements

The frontend may contain demonstration panels for:
- Category suggestions.
- Severity or priority suggestions.
- Photo-analysis feedback.
- Duplicate detection.
- Community assistant.
- Admin assistant.
- Trend analysis or forecasting.

A future assistant interface may display English, Hindi, or Hinglish examples if this fits the agreed product scope.

### Restrictions
- Do not call AI services.
- Do not expose API keys.
- Do not claim a prediction is accurate or authoritative.
- Do not make automatic moderation decisions.
- Do not implement actual forecasting.
- Clearly label sample AI responses as illustrative or demonstration content.
- Add integration notes for the responsible AI teammate.

---

## 10. Design and Accessibility Requirements

### 10.1 Visual Design
- Use a consistent color palette and typography.
- Maintain clear visual hierarchy.
- Use consistent spacing.
- Use reusable cards, buttons, forms, and badges.
- Keep resident and admin interfaces visually distinguishable.
- Avoid unnecessary visual clutter.

### 10.2 Responsive Design
- Support desktop, tablet, and mobile screens.
- Avoid horizontal overflow.
- Ensure navigation works on small screens.
- Stack cards and form controls appropriately on narrow screens.
- Keep map controls usable on mobile.

### 10.3 Accessibility
- Use semantic HTML elements.
- Associate form labels with their controls.
- Provide keyboard-accessible buttons and links.
- Include visible focus states.
- Use sufficient color contrast.
- Do not communicate status through color alone.
- Provide alternative text for meaningful images.
- Use understandable validation and error messages.

---

## 11. Frontend Interaction Requirements

JavaScript may be used for:
- Password visibility controls.
- Client-side form validation.
- Image preview and removal.
- Mock-data search.
- Filtering and sorting.
- Navigation menu interactions.
- Demonstration alerts.
- Local notification read/unread states.
- Map markers and popups.
- Demonstration-only moderation controls.
- Opening and closing dialogs or panels.

These interactions must remain within the browser and must not imply backend persistence.

---

## 12. Out of Scope

The following are explicitly outside the frontend assignment:

- Django backend implementation.
- Database models or migrations.
- Database queries or persistence.
- Backend views or URL handlers.
- REST API creation or integration.
- Real authentication or authorization.
- Account creation or password reset processing.
- Actual report submission to a server.
- Real moderation decisions.
- Persistent voting or confirmation counts.
- Real notification delivery.
- AI service integration.
- AI-based image analysis.
- AI-based classification or severity prediction.
- Actual duplicate detection services.
- Predictive analytics or forecasting services.
- Deployment or infrastructure changes unless separately approved.

Do not create these features as part of the frontend task.

---

## 13. Integration Boundaries

The frontend may need future integration with the backend and AI teammates.

For future integration:
- Use comments to identify where real data may be connected.
- Keep mock data separate from presentation logic where practical.
- Avoid hardcoding assumed API paths.
- Avoid assuming request or response structures.
- Record questions that require agreement with the responsible teammate.
- Replace demonstration data only after the agreed interface contract is provided.

The frontend must remain demonstrable without a backend.

---

## 14. Testing and Quality Checklist

### Pages
- [ ] All 11 required pages have separate templates.
- [ ] Shared components are reused where appropriate.
- [ ] Navigation links work between available frontend pages.
- [ ] Each page has a clear title and heading.

### Forms and Interactions
- [ ] Login validation works in the browser.
- [ ] Registration validation works in the browser.
- [ ] Password visibility controls work.
- [ ] Image preview and removal work.
- [ ] Explore Issues search and filters work.
- [ ] Notification filters and demo read states work.
- [ ] Demo moderation controls provide feedback.
- [ ] No interaction claims to save data to a backend.

### Map
- [ ] Leaflet map initializes when resources are available.
- [ ] OpenStreetMap tiles load when network access is available.
- [ ] Valid mock coordinates produce markers.
- [ ] Missing coordinates are handled gracefully.
- [ ] Map popups and detail navigation work.

### Responsive Design and Accessibility
- [ ] Pages work on desktop.
- [ ] Pages work on tablet.
- [ ] Pages work on mobile.
- [ ] Forms have labels.
- [ ] Keyboard focus is visible.
- [ ] Text and controls are readable.
- [ ] Empty and error states are understandable.

### Scope and Repository Safety
- [ ] All mock data is clearly labelled.
- [ ] No backend logic has been added.
- [ ] No database or API integration has been added.
- [ ] No real authentication has been added.
- [ ] No AI services have been connected.
- [ ] Existing repository work has been preserved.
- [ ] No Git commit, push, or branch switch has occurred without explicit permission.

---

## 15. Definition of Done

The frontend is ready for review when:
1. All required page templates exist or have been adapted to the existing repository.
2. Shared components and styles are organized.
3. Navigation and demonstration interactions work.
4. Mock data is clearly labelled.
5. The map works with valid demonstration coordinates when its resources are available.
6. Pages are responsive and basic accessibility requirements are addressed.
7. The application can be demonstrated without a backend.
8. Backend and AI integration points are documented without implementing those services.
9. Existing work has been preserved.
10. All changes remain within the assigned frontend scope.

## 16. Final Instruction to the Development Assistant

Before making major changes, inspect the existing repository and explain its current structure. Read this PRD together with `plan.md`. Propose a staged implementation approach, preserve existing work, and explain each step in beginner-friendly language.

**Frontend only. No React. No backend. No database. No APIs. No authentication processing. No AI services. No Git commit, push, or branch switch without explicit permission.**
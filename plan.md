# NagarWatch Frontend Implementation Plan

## 1. Project Overview

**Project Name:** NagarWatch  
**Project:** PS 1.1  
**Role:** Frontend Developer  
**Team Size:** 4 members

NagarWatch is a civic issue reporting and monitoring platform. Residents can report local problems, explore reported issues, view their locations on a map, and track report statuses. Administrators can review and moderate reports through an admin dashboard.

This plan covers **frontend development only**. Backend, database, authentication processing, and AI services are outside my assigned responsibility.

## 2. Technology Stack

- HTML5
- CSS3
- JavaScript
- Django Templates
- Leaflet.js for interactive maps
- OpenStreetMap for map tiles
- Mock/sample data for frontend demonstrations

**Important:** Do not use React. Do not implement backend functionality or real AI services.

## 3. Frontend Development Rules

1. Every page must have its own separate HTML template.
2. Shared elements may use reusable Django template files.
3. Use Django template inheritance where appropriate.
4. Keep HTML, CSS, and JavaScript organized in separate files.
5. Clearly label mock data as demonstration data.
6. Do not invent backend API endpoints, request fields, or response formats.
7. Add comments wherever backend or AI integration may be needed later.
8. Do not overwrite existing work without inspecting it first.
9. Do not commit, push, or switch Git branches without explicit permission.
10. Explain changes in beginner-friendly language.

## 4. Proposed Folder Structure

Inspect the existing repository before creating or modifying files. Adapt this structure to the current project rather than deleting existing work.

```text
NagarWatch/
├── README.md
├── plan.md
├── prd.md
├── .gitignore
├── templates/
│   ├── base.html
│   ├── components/
│   │   ├── navbar.html
│   │   ├── footer.html
│   │   ├── report_card.html
│   │   ├── status_badge.html
│   │   ├── priority_badge.html
│   │   ├── alert.html
│   │   └── empty_state.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── resident/
│   │   ├── dashboard.html
│   │   ├── report_issue.html
│   │   ├── explore_issues.html
│   │   ├── issue_detail.html
│   │   ├── map_view.html
│   │   ├── my_reports.html
│   │   └── notifications.html
│   └── admin/
│       ├── dashboard.html
│       └── moderation.html
└── static/
    ├── css/
    │   ├── base.css
    │   ├── components.css
    │   ├── responsive.css
    │   └── pages/
    │       ├── auth.css
    │       ├── dashboard.css
    │       ├── report_issue.css
    │       ├── explore_issues.css
    │       ├── issue_detail.css
    │       ├── map_view.css
    │       ├── my_reports.css
    │       ├── notifications.css
    │       └── moderation.css
    ├── js/
    │   ├── base.js
    │   ├── report_issue.js
    │   ├── explore_issues.js
    │   ├── map_view.js
    │   ├── notifications.js
    │   └── moderation.js
    └── images/
```

This is a proposed structure, not permission to replace the existing repository layout. Inspect the current files first and make only necessary changes.

## 5. Shared Frontend Components

### `base.html`
- Common HTML document structure.
- Shared CSS and JavaScript references.
- Page title blocks.
- Main content block.
- Optional navigation and footer blocks.

### `components/navbar.html`
- Resident navigation.
- Admin navigation where appropriate.
- Responsive mobile menu.
- Active navigation styling.
- Profile and logout interface placeholders.

### `components/footer.html`
- Basic footer.
- Project name and relevant links.

### `components/report_card.html`
- Issue title.
- Category.
- Location.
- Date.
- Status.
- Priority.
- Link or button to view details.

### `components/status_badge.html`
Display issue statuses consistently.

### `components/priority_badge.html`
Display priority levels consistently.

### `components/alert.html`
Reusable success, warning, error, and information messages.

### `components/empty_state.html`
Reusable messages and actions for pages with no results.

## 6. Pages to Develop

### Page 1: Login
**Template:** `templates/auth/login.html`

Include:
- Email or username input, depending on the agreed project requirements.
- Password input.
- Show/hide password button.
- Client-side form validation.
- Login button.
- Link to registration.
- Forgot-password placeholder.

Do not implement real authentication.

### Page 2: Registration
**Template:** `templates/auth/register.html`

Include:
- Name field if required by the agreed requirements.
- Email field.
- Password and confirm-password fields.
- Show/hide password controls.
- Client-side validation.
- Password-match validation.
- Link back to login.

Do not create real accounts or save user data.

### Page 3: Resident Dashboard
**Template:** `templates/resident/dashboard.html`

Include:
- Welcome section.
- Total reports.
- Open reports.
- In-progress reports.
- Resolved reports.
- Recent issue cards.
- Quick action to report a problem.
- Links to Explore Issues, Map, My Reports, and Notifications.

All sample counts must be labelled as demonstration data.

### Page 4: Report an Issue
**Template:** `templates/resident/report_issue.html`

Include:
- Issue title.
- Description.
- Category selector.
- Photo upload.
- Image preview and removal.
- Location input.
- Optional latitude and longitude fields.
- Map-based location selection if feasible.
- Optional browser geolocation after the user clicks a location button.
- Submit and cancel controls.
- Check Similar Reports button.
- UI placeholders for AI category suggestions, severity estimation, photo analysis, and duplicate detection.

The form must not save reports to a backend. Any demonstration result must be clearly labelled.

### Page 5: Explore Issues
**Template:** `templates/resident/explore_issues.html`

Include:
- Search input.
- Category filter.
- Status filter.
- Priority filter.
- Sort controls.
- Clear filters button.
- Report cards.
- Loading, empty, and error states.

Search and filtering may operate on local mock data.

### Page 6: Issue Details
**Template:** `templates/resident/issue_detail.html`

Include:
- Issue title and description.
- Category and location.
- Photo if available.
- Submission date.
- Status and priority.
- Status timeline.
- AI suggestion panel placeholder.
- Similar reports section.
- Confirm and Dispute buttons.
- View Location button.
- Back navigation.

Confirmation and dispute interactions must remain demonstration-only. Do not persist votes.

### Page 7: Map View
**Template:** `templates/resident/map_view.html`

Include:
- Leaflet map.
- OpenStreetMap tiles.
- Markers for mock reports with valid coordinates.
- Marker popups with basic report information.
- Search and filters if feasible.
- View Details action.
- A helpful message when coordinates are unavailable.

Viewing the map must not require location permission. Do not fabricate exact locations for reports without coordinates.

### Page 8: My Reports
**Template:** `templates/resident/my_reports.html`

Include:
- Mock list of the current resident's reports.
- Status and date information.
- Priority indicators.
- Status progress where applicable.
- Search or filter controls.
- Links to issue details.
- Report New Issue action.
- Empty state.

Do not implement real user-specific data retrieval.

### Page 9: Notifications
**Template:** `templates/resident/notifications.html`

Include:
- Notification list using mock data.
- All and Unread filters.
- Mark as Read and Mark All Read buttons.
- Links to related reports.
- Empty state.

Read/unread changes may exist only in browser memory during the demonstration.

### Page 10: Admin Dashboard
**Template:** `templates/admin/dashboard.html`

Include:
- Pending, verified, in-progress, and resolved report counts.
- High-priority report count.
- Recent reports.
- Category breakdown.
- Trend visualization if feasible.
- Priority overview.
- AI-generated summary placeholder.
- Links to moderation and report details.

All metrics and summaries must use clearly labelled mock data.

### Page 11: Admin Moderation
**Template:** `templates/admin/moderation.html`

Include:
- Report title and description.
- Photo and location information.
- Status and priority.
- AI category and severity suggestions.
- Possible duplicate reports.
- Community confirmation/dispute counts.
- Report history.
- Verify, Reject, Mark Duplicate, Change Status, View Similar, and Save Decision controls as appropriate.

These controls must not modify backend records. Do not automatically reject, merge, or delete reports.

## 7. JavaScript Responsibilities

Use JavaScript only for frontend interactions, such as:

- Showing and hiding passwords.
- Validating required fields.
- Previewing selected images.
- Searching and filtering mock reports.
- Sorting mock reports.
- Opening and closing menus or dialogs.
- Displaying demonstration alerts.
- Updating local notification read states.
- Rendering map markers from mock data.
- Demonstrating confirmation and dispute buttons without persistence.

Keep mock data separate from page interaction code when practical.

Do not implement API calls, server-side processing, authentication, or AI service requests.

## 8. Visual Design and Responsiveness

Use a consistent civic-tech design:
- Clear navigation.
- Readable typography.
- Consistent spacing.
- Accessible contrast.
- Reusable buttons, cards, badges, and forms.
- Responsive layouts for desktop, tablet, and mobile.
- Clear distinction between resident and admin interfaces.
- Helpful empty states and validation messages.
- Visible labels for mock content and unavailable functionality.

Avoid adding unnecessary libraries or dependencies.

## 9. Implementation Stages

### Stage 1: Inspect the Repository
- Confirm the current branch and working tree.
- Review existing templates, static files, and project configuration.
- Identify existing work that must be preserved.
- Explain the current structure before making major changes.

### Stage 2: Establish the Shared Foundation
- Organize the shared template structure.
- Add or improve `base.html`.
- Create shared components where useful.
- Establish the global CSS and responsive styling.

### Stage 3: Build Authentication Interfaces
- Develop login and registration templates.
- Add client-side validation.
- Clearly communicate that authentication is not connected.

### Stage 4: Build Resident Pages
Develop the resident dashboard, report form, explore page, issue details, map, My Reports, and Notifications.

### Stage 5: Build Admin Pages
Develop the admin dashboard and moderation interface using mock data.

### Stage 6: Add Frontend Interactions
Add validation, filters, sorting, image preview, map markers, and demonstration-only actions.

### Stage 7: Review and Test
- Check that each page has its own template.
- Check navigation and template inheritance.
- Test responsive layouts.
- Check forms and browser interactions.
- Verify that mock data is clearly labelled.
- Confirm that no backend or AI functionality has been added.
- Report any integration requirements for the backend/AI teammates.

Work in small, reviewable stages. Explain each stage in beginner-friendly language.

## 10. Completion Checklist

- [ ] Repository inspected before changes.
- [ ] Existing work preserved.
- [ ] All 11 page templates created or appropriately adapted.
- [ ] Shared components reused where appropriate.
- [ ] HTML, CSS, and JavaScript kept organized.
- [ ] Django Templates used; no React.
- [ ] Mock data clearly labelled.
- [ ] Leaflet/OpenStreetMap map works with valid mock coordinates.
- [ ] Forms and filters have frontend-only interactions.
- [ ] Responsive layouts checked.
- [ ] Accessibility basics reviewed.
- [ ] Backend/AI integration points documented.
- [ ] No backend, database, API, authentication processing, or AI services implemented.
- [ ] No Git commit, push, or branch switch without explicit permission.

## 11. Final Instruction

The assigned responsibility is frontend development only. Inspect the current repository first, explain the existing structure, and propose the implementation approach before making major changes. Follow this plan together with `prd.md`, preserve existing work, and ask for permission before any Git operation that commits, pushes, or switches branches.
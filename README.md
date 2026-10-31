# NagarWatch
# 🏙️ NagarWatch

**A civic issue reporting platform that lets residents report local problems (potholes, garbage, water leaks, broken streetlights, etc.), see them on a live map, and helps authorities track and resolve them.**

> Problem Statement: PS 1.1 — Civic Tech

<!-- Add badges if you like -->
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-5.x-green)
![Leaflet](https://img.shields.io/badge/Leaflet-Maps-brightgreen)

---

## 📌 Table of Contents
1. [Overview](#-overview)
2. [Features](#-features)
3. [Tech Stack](#-tech-stack)
4. [System Architecture](#-system-architecture)
5. [Project Structure](#-project-structure)
6. [Installation & Setup](#-installation--setup)
7. [Environment Variables](#-environment-variables)
8. [API Reference](#-api-reference)
9. [Frontend Details](#-frontend-details)
10. [Backend Details](#-backend-details)
11. [AI Integration](#-ai-integration)
12. [Screenshots](#-screenshots)
13. [Roadmap](#-roadmap)
14. [Contributing](#-contributing)
15. [Team](#-team)
16. [License](#-license)

---

## 🔎 Overview

Cities struggle with slow, untracked complaint handling. **NagarWatch** gives residents a simple way to report issues with a location and photo, shows every reported issue on an interactive map, and gives authorities a dashboard to prioritise and resolve them. AI is used to *[describe: categorise issues / detect duplicates / estimate severity / summarise complaints]*.

## ✨ Features

**For Residents**
- Register / log in and report an issue with title, description, category, photo and location
- Pick location on the map or use current GPS location
- View all reported issues on an interactive map (Leaflet + OpenStreetMap)
- Track status of own reports (Reported → In Progress → Resolved)

**For Authorities / Admin**
- Dashboard to view, filter and update issues
- Status management and assignment *(update if applicable)*
- Analytics on issue categories and areas *(update if applicable)*

**AI-powered**
- *[Fill in: e.g., automatic category detection from text/image, severity scoring, duplicate detection, chatbot, summary]*

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5, CSS3, JavaScript, Django Templates, Leaflet.js, OpenStreetMap tiles |
| Backend | Python, Django *(add Django REST Framework if used)* |
| Database | SQLite (dev) / *[PostgreSQL if used]* |
| AI / ML | *[e.g., Google Gemini API / OpenAI API / Anthropic Claude API / scikit-learn]* |
| Other | *[Pillow for image uploads, etc.]* |

## 🧩 System Architecture

```
┌──────────────┐     HTTP/JSON      ┌────────────────────┐      ┌────────────┐
│   Browser    │ ─────────────────▶ │   Django Backend   │ ───▶ │  Database  │
│ Templates +  │ ◀───────────────── │ Views / API / Auth │ ◀─── │  (SQLite)  │
│ Leaflet JS   │                    └─────────┬──────────┘      └────────────┘
└──────────────┘                              │
                                              ▼
                                     ┌─────────────────┐
                                     │   AI Service    │
                                     │ (LLM / ML model)│
                                     └─────────────────┘
```

## 📁 Project Structure

> Update this to match your repo exactly.

```
NagarWatch/
├── manage.py
├── requirements.txt
├── nagarwatch/            # Project settings, urls, wsgi/asgi
├── <app_name>/            # Main Django app (models, views, urls, serializers)
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── ...
├── templates/
│   └── resident/
│       └── map_view.html
├── static/
│   ├── css/
│   └── js/
│       └── map_view.js
└── media/                 # Uploaded issue images
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- pip and virtualenv
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/tanmayk1401-arch/NagarWatch.git
cd NagarWatch

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file (see Environment Variables below)

# 5. Apply migrations
python manage.py makemigrations
python manage.py migrate

# 6. Create an admin user
python manage.py createsuperuser

# 7. Run the server
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

## 🔐 Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
AI_API_KEY=your-ai-provider-api-key
```

> ⚠️ Never commit `.env` or API keys to GitHub. Add `.env` to `.gitignore`.

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/issues/` | List all reported issues (used by the map view) |
| POST | `/api/issues/` | Create a new issue *(update if applicable)* |
| GET | `/api/issues/<id>/` | Get details of one issue *(update if applicable)* |
| PATCH | `/api/issues/<id>/` | Update status *(admin only, update if applicable)* |

**Sample response – `GET /api/issues/`**

```json
[
  {
    "id": 1,
    "title": "Large pothole on main road",
    "category": "Road",
    "description": "Deep pothole near the market",
    "latitude": 26.9124,
    "longitude": 75.7873,
    "status": "reported",
    "created_at": "2026-10-30T10:15:00Z"
  }
]
```

## 🎨 Frontend Details

- **Templates:** Django templates under `templates/` (resident pages, e.g. `resident/map_view.html`)
- **Map:** Leaflet.js with OpenStreetMap tiles, implemented in `static/js/map_view.js`
- **Data loading:** the map fetches issues from `/api/issues/` and renders a marker with a popup for each issue
- **Styling:** *[Bootstrap / Tailwind / custom CSS]*
- **Responsive:** designed to work on desktop and mobile

## ⚙️ Backend Details

- **Framework:** Django
- **Authentication:** Django auth with separate resident and admin/authority roles *(update)*
- **Models:** `Issue` (title, description, category, location, image, status, timestamps, reporter) *(update with your real fields)*
- **Views / API:** JSON endpoint(s) at `/api/issues/` consumed by the frontend
- **File uploads:** issue images stored in `media/`
- **Admin panel:** available at `/admin/`

## 🤖 AI Integration

> Fill this section with your real implementation.

- **Purpose:** *[what the AI does, e.g. auto-categorise complaints, assess severity, detect duplicates, generate summaries]*
- **Model / Provider:** *[e.g. Gemini, OpenAI, Claude, custom ML model]*
- **Where it runs:** *[e.g. `issues/ai_service.py`, called when an issue is submitted]*
- **Input → Output:** *[e.g. issue description + image → category + priority score]*
- **Fallback:** *[what happens if the AI API fails or key is missing]*

**Flow**

```
Resident submits issue → Backend sends text/image to AI → AI returns category/priority
→ Result saved with the issue → Shown on map & authority dashboard
```

## 📸 Screenshots

| Home | Map View | Report Issue |
|------|----------|--------------|
| ![Home](docs/home.png) | ![Map](docs/map.png) | ![Report](docs/report.png) |

## 🗺️ Roadmap

- [ ] Email / SMS notifications on status change
- [ ] Upvote / "me too" on existing issues
- [ ] Authority-wise issue routing
- [ ] Analytics dashboard with heatmaps
- [ ] Mobile app / PWA

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

## 👥 Team - VIGIL

- **Tanmay Kapoor** — [@tanmayk1401-arch](https://github.com/tanmayk1401-arch)
- **Divyam Chechani** - (https://github.com/divyamchechani)
- **Himanshu Raj**
- **Divya Rathore

## 📄 License

This project is licensed under the MIT License — see the `LICENSE` file for details.

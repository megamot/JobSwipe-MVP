# Copilot Instructions for JobSwipe

## Project Overview
- **Purpose:** MVP job search app with Tinder-like swipe UI.
- **Stack:** Python (Flask), MongoDB (Docker/Atlas), HTML/CSS/JS (no major frameworks).
- **Key Files:**
  - `app.py`: Flask API, vacancy endpoints, MongoDB connection.
  - `parser.py`: Data ingestion/parsing from Robota.ua, tagging logic.
  - `tagging_config.py`: Tag generation for vacancies/companies.
  - `index.html`, `details.html`: Swipe UI and vacancy details.
  - `docker-compose.yml`: Local MongoDB setup.

## Architecture & Data Flow
- **MongoDB Collections:**
  - `vacancies`: All fields from Robota.ua `/company/{id}/vacancies` API.
  - `companies`: All fields from Robota.ua `/company/{id}` API.
  - `users`: User profiles, selected tags, swipe history (`liked_vacancies`, `rejected_vacancies`).
- **Parser Workflow:**
  1. For each company in `COMPANY_IDS`, fetch company data and save to `companies`.
  2. Fetch all vacancies for each company, save all fields to `vacancies`.
  3. Tagging is performed on a copy of data, not the original document.
  4. Use upsert (`update_one(..., upsert=True)`) for daily sync.

## Developer Workflows
- **Run Backend:**
  - `python app.py` (Flask API)
- **Run Parser:**
  - `python parser.py` (fetches/updates data)
- **Test DB Connection:**
  - `python test_db.py`
- **MongoDB Local:**
  - Use `docker-compose up` (see `docker-compose.yml` for credentials)
- **Install Requirements:**
  - `pip install -r requirements.txt`

## Project-Specific Patterns
- **Tagging:**
  - Tag logic in `tagging_config.py` (see `TECH_DIRECTION_TAGS`, `ROBOTA_LEVEL_MAPPING`).
  - Tags are stored in `tags_tech`, `tags_company` fields.
- **Vacancy Filtering:**
  - `/api/vacancies` endpoint should filter by tags matching user profile (see ТЗ).
- **Swipe Logic:**
  - `/api/swipe` endpoint records user reactions in `users` collection.
- **City Display:**
  - Show "Київ" for `cityId: 1`, else show `cityId` value.
- **Frontend:**
  - Mobile-first, adaptive card UI in `index.html`.
  - Vacancy details in `details.html`.

## Git & Branching
- Use feature branches for new functionality (e.g., `feat/auth-user-profile`).
- Commit messages: `[Feat/Fix/Chore]: Description` (one logical change per commit).
- Always update relevant files (`app.py`, `parser.py`, HTML/JS) in each commit.

## Integration Points
- Robota.ua API: `/company/{id}` and `/company/{id}/vacancies`.
- MongoDB: Local via Docker, or Atlas.

---

**For more details, see the ТЗ in `copilot-instructions.md` at project root.**

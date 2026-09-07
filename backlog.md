# Backlog — Shared Household Chores Manager (Django)

1. **Project setup** — add `chores_app` to `INSTALLED_APPS`, configure PostgreSQL, set up `requirements.txt`
2. **Models** — `Household`, `Member` (user + role), `Chore` (title, points, due date, status, claimant), `PointLog`
3. **Auth** — Google OAuth integration (e.g., `django-allauth`), household invitation flow
4. **Chore board views** — list unclaimed chores, create/edit chores, claim/unclaim actions
5. **Complete + dispute flow** — self-mark done, dispute window logic, auto-award points after window closes
6. **Leaderboard view** — per-household standings with points
7. **Escalating reminders** — scheduled task (e.g., Celery beat or Django cron) to bump reminder level on unclaimed chores
8. **Templates/UI** — base template, dashboard, chore board, leaderboard pages
9. **Docker setup** — Dockerfile + docker-compose with PostgreSQL service
10. **Tests** — model, view, and auth tests

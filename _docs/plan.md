# Shared Household Chores Manager — MVP Scope

## Users & Households
- Closed group (2-6 members), invited to a shared household
- Google OAuth login
- Any member can create/edit chores; household owner (admin) can override anything

## Chores
- Members post chores with a point value and optional due date
- Claim-based: members voluntarily claim chores from a shared board
- Self-mark complete; household can dispute/flag within a time window

## Reminders
- Unclaimed chores get escalating in-app reminders until someone claims them
- No email in MVP

## Points & Leaderboard
- Completed chores award points automatically
- Leaderboard shows standings per household

## Tech Stack
- Backend: Python / FastAPI
- Frontend: React (TypeScript)
- Database: PostgreSQL
- Auth: Google OAuth
- Deployment: Docker / docker-compose (self-hosted)

## Out of Scope (for now)
- Email/push notifications, chore rotation, chore templates, photo proof, peer verification, multiple households per user

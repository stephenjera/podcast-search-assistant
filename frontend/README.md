# Frontend

React + TypeScript + Tailwind CSS v4 SPA for podcast search.

## Prerequisites

- Node.js 20+
- npm

## Install Dependencies

```bash
cd frontend
npm install
```

## Configure API Base URL

The frontend calls backend API through `VITE_API_BASE_URL`.

Create `.env.local` in `frontend/`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

If omitted, the app defaults to `http://localhost:8000`.

## Run Dev Server

```bash
cd frontend
npm run dev
```

Default dev URL: `http://localhost:5173`.

## Current UX Flows

- Global natural-language search across episodes
- Optional episode-scoped search through an episode card browser with title filter
- Result cards with score, timestamp label, and excerpt snippet

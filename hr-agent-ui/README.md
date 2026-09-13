# HR Agent Studio — Vercel-Style Design

A refined, minimalist web console designed according to the **Vercel Design System** (Geist typography, high-contrast dark palette, clean borders, and crisp card layouts) for the **Frappe HR Operations Agent**.

---

## 1. Environment & Base URL Configuration

The frontend dynamically points to your backend using standard environment variables.

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Contents of `.env`:
```env
# Target API Base URL (leave empty to use local Vite reverse proxy)
VITE_API_BASE_URL=http://localhost:8001

# Model ID identifier
VITE_MODEL_NAME=hr-agent
```

---

## 2. Features

- **Vercel AI SDK Integration**: Built with `ai` & `@ai-sdk/react` architecture principles with streaming OpenAI-compatible completions.
- **Geist Design Tokens**: Custom Geist sans and mono typography, crisp `#1f1f1f` borders, minimal cards, and pure black `#000000` canvas.
- **Approvals & Governance Panel**: Live polling of mutation requests, payload inspector, and one-click execution or rejection.
- **Discovered MCP Infrastructure Monitoring**: Real-time status badges for backend connectivity, active model provider, and Frappe MCP server status.

---

## 3. Development & Production

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```
Visit [http://localhost:5173](http://localhost:5173) in your browser.

import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
    channel: process.env.CI ? "chromium" : "msedge",
  },
  webServer: [
    {
      command: "python -m backend.browser_server",
      cwd: "..",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1",
      url: "http://127.0.0.1:5173",
      env: { VITE_API_BASE_URL: "http://127.0.0.1:8000" },
      reuseExistingServer: false,
    },
  ],
});

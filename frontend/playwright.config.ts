import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  reporter: "line",
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:8000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1280, height: 800 } } },
    { name: "tablet", use: { viewport: { width: 800, height: 900 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 } } },
  ],
});

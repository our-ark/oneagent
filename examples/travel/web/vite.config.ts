import { defineConfig } from "vite";
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        flights: "flights/index.html",
        hotels: "hotels/index.html",
        activities: "activities/index.html",
      },
    },
  },
  server: { strictPort: true, proxy: { "/api": "http://127.0.0.1:8080" } },
});

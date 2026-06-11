import React from "react";
import ReactDOM from "react-dom/client";
// Default font (Space Grotesk), self-hosted — offline-friendly, no external
// request. Other picker fonts load from Google Fonts on demand — see src/fonts.ts.
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import { App } from "./App.tsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

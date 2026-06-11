// Font themes you can switch between live (header → "Aa").
// Each theme sets --font-display (headings) and --font-body (everything else).
// Fonts load on demand from Google Fonts; after first load the PWA caches them.
// For production self-hosting, swap to @fontsource packages (see note in README).

const SANS =
  "ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
const SERIF = "ui-serif, Georgia, Cambria, 'Times New Roman', serif";

export interface FontTheme {
  id: string;
  label: string;
  note: string; // one-line "what it feels like"
  display: string; // CSS font-family for headings
  body: string; // CSS font-family for body text
  google: string[] | null; // Google Fonts family specs, or null for system
}

export const FONT_THEMES: FontTheme[] = [
  {
    id: "space",
    label: "Space Grotesk",
    note: "Geometric, distinctive — the default",
    display: `'Space Grotesk', ${SANS}`,
    body: `'Space Grotesk', ${SANS}`,
    google: ["Space+Grotesk:wght@400;500;600;700"],
  },
  {
    id: "plex",
    label: "IBM Plex",
    note: "Engineered, researcher-ish character",
    display: `'IBM Plex Sans', ${SANS}`,
    body: `'IBM Plex Sans', ${SANS}`,
    google: ["IBM+Plex+Sans:wght@400;500;600;700"],
  },
  {
    id: "vollkorn",
    label: "Vollkorn",
    note: "Warm book serif with character",
    display: `'Vollkorn', ${SERIF}`,
    body: `'Vollkorn', ${SERIF}`,
    google: ["Vollkorn:wght@400;500;600;700"],
  },
  {
    id: "spectral",
    label: "Spectral",
    note: "Elegant serif designed for screens",
    display: `'Spectral', ${SERIF}`,
    body: `'Spectral', ${SERIF}`,
    google: ["Spectral:wght@400;500;600"],
  },
];

const injected = new Set<string>();

function injectFamilies(families: string[]): void {
  const url =
    "https://fonts.googleapis.com/css2?" +
    families.map((f) => `family=${f}`).join("&") +
    "&display=swap";
  if (injected.has(url)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = url;
  document.head.appendChild(link);
  injected.add(url);
}

/** Apply a theme: load its fonts (if any) and set the CSS variables. */
export function applyFontTheme(theme: FontTheme): void {
  if (theme.google) injectFamilies(theme.google);
  const root = document.documentElement.style;
  root.setProperty("--font-display", theme.display);
  root.setProperty("--font-body", theme.body);
}

/** Preload every theme's fonts so the picker previews render in their real face. */
export function preloadAllFonts(): void {
  for (const t of FONT_THEMES) if (t.google) injectFamilies(t.google);
}

const KEY = "swenia.font";
const DEFAULT_FONT_ID = "space"; // Space Grotesk — the default

export function savedFont(): FontTheme {
  const id = localStorage.getItem(KEY);
  return (
    FONT_THEMES.find((t) => t.id === id) ??
    FONT_THEMES.find((t) => t.id === DEFAULT_FONT_ID) ??
    FONT_THEMES[0]
  );
}

export function saveFont(id: string): void {
  localStorage.setItem(KEY, id);
}

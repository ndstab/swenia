// TypeScript mirror of the digest contract written by the Python pipeline
// (swenia/digest.py → output/latest.json). Keep in sync with card_dict().

export type Tier = "must_know" | "worth_knowing" | "skim" | "drop";
export type Category = "headline" | "frontier";

export interface Source {
  name: string;
  url: string;
}

export interface Card {
  id: string;
  tier: Tier;
  category: Category;
  title: string;
  why_it_matters: string;
  summary: string;
  tags: string[];
  sources: Source[];
  published: string | null;
  score: number;
}

export interface Section {
  key: "headlines" | "frontier";
  title: string;
  cards: Card[];
}

export interface Digest {
  date: string;
  generated_at: string;
  summary_line: string;
  counts: { total: number; headlines: number; frontier: number };
  sections: Section[];
}

export const TIER_LABEL: Record<Tier, string> = {
  must_know: "Must know",
  worth_knowing: "Worth knowing",
  skim: "Skim",
  drop: "",
};

// Subtle accent per tier (the only color in an otherwise monochrome UI).
export const TIER_COLOR: Record<Tier, string> = {
  must_know: "#e5484d",
  worth_knowing: "#f5a623",
  skim: "#9b9b9b",
  drop: "#9b9b9b",
};

export async function loadDigest(): Promise<Digest> {
  const res = await fetch("/latest.json", { cache: "no-cache" });
  if (!res.ok) throw new Error(`digest fetch failed: ${res.status}`);
  return (await res.json()) as Digest;
}

/** Flatten sections into one ordered deck: headlines first, then frontier. */
export function toDeck(digest: Digest): Card[] {
  const order = ["headlines", "frontier"];
  return [...digest.sections]
    .sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key))
    .flatMap((s) => s.cards);
}

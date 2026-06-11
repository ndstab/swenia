import { useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { type Card, type Digest, loadDigest, toDeck } from "./digest.ts";
import { SwipeCard } from "./SwipeCard.tsx";
import { CaughtUp } from "./CaughtUp.tsx";
import { FontPicker } from "./FontPicker.tsx";
import { applyFontTheme, type FontTheme, savedFont, saveFont } from "./fonts.ts";
import "./app.css";

type State =
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "ready"; digest: Digest; deck: Card[] };

export function App() {
  const [state, setState] = useState<State>({ phase: "loading" });
  const [index, setIndex] = useState(0);
  const [font, setFont] = useState<FontTheme>(() => savedFont());
  const [pickerOpen, setPickerOpen] = useState(false);

  useEffect(() => {
    applyFontTheme(font); // apply saved font on mount and whenever it changes
  }, [font]);

  function pickFont(t: FontTheme) {
    setFont(t);
    saveFont(t.id);
  }

  useEffect(() => {
    loadDigest()
      .then((digest) =>
        setState({ phase: "ready", digest, deck: toDeck(digest) }),
      )
      .catch((e) => setState({ phase: "error", message: String(e) }));
  }, []);

  if (state.phase === "loading") {
    return <div className="screen center muted">Loading today’s digest…</div>;
  }
  if (state.phase === "error") {
    return (
      <div className="screen center">
        <p className="muted">Couldn’t load the digest.</p>
        <p className="faint small">{state.message}</p>
      </div>
    );
  }

  const { digest, deck } = state;
  const done = index >= deck.length;

  return (
    <div className="screen">
      <Header digest={digest} done={done} onFont={() => setPickerOpen(true)} />

      {!done && <Progress total={deck.length} index={index} />}

      <FontPicker
        open={pickerOpen}
        current={font.id}
        onPick={pickFont}
        onClose={() => setPickerOpen(false)}
      />

      <main className="deck">
        {done ? (
          <CaughtUp digest={digest} onReview={() => setIndex(0)} />
        ) : (
          <AnimatePresence>
            {/* Render only a small window of cards for the stack effect. */}
            {deck
              .map((card, i) => ({ card, i }))
              .filter(({ i }) => i >= index && i < index + 3)
              .reverse()
              .map(({ card, i }) => (
                <SwipeCard
                  key={card.id}
                  card={card}
                  depth={i - index}
                  isTop={i === index}
                  onDismiss={() => setIndex((n) => n + 1)}
                />
              ))}
          </AnimatePresence>
        )}
      </main>
    </div>
  );
}

function Progress({ total, index }: { total: number; index: number }) {
  const n = String(index + 1).padStart(2, "0");
  const t = String(total).padStart(2, "0");
  return (
    <div className="progress">
      <span className="count">
        {n} / {t}
      </span>
      <div className="track">
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            className={"seg" + (i < index ? " done" : i === index ? " active" : "")}
          />
        ))}
      </div>
    </div>
  );
}

function Header({
  digest,
  done,
  onFont,
}: {
  digest: Digest;
  done: boolean;
  onFont: () => void;
}) {
  void done;
  // Swiss masthead: wordmark• + ISO-ish date, under a strong rule.
  const date = digest.date.replace(/-/g, "·");
  return (
    <header className="topbar">
      <div className="brand">swenia</div>
      <div className="topbar-right">
        <div className="sub">{date}</div>
        <button className="aa-btn" onClick={onFont} aria-label="Change font">
          Aa
        </button>
      </div>
    </header>
  );
}

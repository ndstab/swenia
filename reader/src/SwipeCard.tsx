import { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useTransform, type PanInfo } from "framer-motion";
import { type Card, TIER_LABEL } from "./digest.ts";

const SWIPE_THRESHOLD = 90; // px past which a release dismisses the card
const FLICK_VELOCITY = 480; // a fast flick dismisses even below the distance threshold
const EXIT_X = 560; // fly fully clear of the widest phone before unmounting

export function SwipeCard({
  card,
  depth,
  isTop,
  onDismiss,
}: {
  card: Card;
  depth: number; // 0 = top, 1 = behind, 2 = further behind
  isTop: boolean;
  onDismiss: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [exitX, setExitX] = useState(0); // committed swipe direction for the exit
  const leaving = useRef(false);
  const x = useMotionValue(0);
  // fade + slight rotate as you drag
  const rotate = useTransform(x, [-220, 220], [-7, 7]);
  const opacity = useTransform(x, [-280, -90, 0, 90, 280], [0, 1, 1, 1, 0]);

  // Defer the actual dismissal by one render: this guarantees AnimatePresence
  // reads an `exit` that already points in the swiped direction. (Reading the
  // live motion value at exit time is racy — the released drag springs back to
  // 0 first, which made every swipe exit to the right on touch devices.)
  useEffect(() => {
    if (leaving.current) onDismiss();
  }, [exitX]);

  function handleDragEnd(_: unknown, info: PanInfo) {
    if (leaving.current) return;
    const past = Math.abs(info.offset.x) > SWIPE_THRESHOLD;
    const flicked = Math.abs(info.velocity.x) > FLICK_VELOCITY;
    if (past || flicked) {
      const dir = info.offset.x < 0 || info.velocity.x < 0 ? -1 : 1;
      leaving.current = true;
      setExitX(dir * EXIT_X);
    }
  }

  // Cards behind the top one are nudged down + scaled for a stacked look.
  const restScale = 1 - depth * 0.045;
  const restY = depth * 14;

  return (
    <motion.article
      className="card"
      style={isTop ? { x, rotate, opacity, zIndex: 10 } : { zIndex: 10 - depth }}
      initial={{ scale: restScale, y: restY + 20, opacity: 0 }}
      animate={{ scale: restScale, y: restY, opacity: 1 }}
      exit={{
        x: exitX,
        opacity: 0,
        // long ease-out glide (easeOutQuint-ish) so the card decelerates as it leaves
        transition: {
          x: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
          opacity: { duration: 0.32, ease: "easeOut" },
        },
      }}
      transition={{ type: "spring", stiffness: 210, damping: 26, mass: 1 }}
      drag={isTop && !leaving.current ? "x" : false}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.55}
      dragTransition={{ bounceStiffness: 360, bounceDamping: 34 }}
      onDragEnd={handleDragEnd}
      onClick={() => isTop && !leaving.current && setExpanded((e) => !e)}
    >
      <div className="card-head">
        <span className={"tier " + card.tier}>
          <span className="mark" />
          {TIER_LABEL[card.tier]}
        </span>
        <span className="category">
          {card.category === "headline" ? "Headline" : "Frontier"}
        </span>
      </div>

      <h2 className="card-title">{card.title}</h2>

      <div className="why">
        <div className="why-rule" />
        <div>
          <span className="label">Why It Matters</span>
          <p>{card.why_it_matters}</p>
        </div>
      </div>

      <div className="summary-block">
        <span className="label">Summary</span>
        <p className={"summary" + (expanded ? " open" : "")}>{card.summary}</p>
      </div>

      <div className="card-foot">
        <div className="tags">
          {card.tags.slice(0, 4).map((t) => (
            <span key={t} className="tag">
              {t}
            </span>
          ))}
        </div>
        <div className="source">
          <span className="src-lbl">Source</span>
          <a
            className="src-name"
            href={card.sources[0]?.url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            {card.sources[0]?.name}
            {card.sources.length > 1 ? ` +${card.sources.length - 1}` : ""}
          </a>
        </div>
      </div>

      {isTop && (
        <div className="hint">
          {expanded ? "tap to collapse" : "tap to expand · swipe to dismiss"}
        </div>
      )}
    </motion.article>
  );
}

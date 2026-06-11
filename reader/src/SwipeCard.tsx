import { useState } from "react";
import { motion, useMotionValue, useTransform, type PanInfo } from "framer-motion";
import { type Card, TIER_LABEL } from "./digest.ts";

const SWIPE_THRESHOLD = 110; // px past which a release dismisses the card

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
  const x = useMotionValue(0);
  // fade + slight rotate as you drag
  const rotate = useTransform(x, [-200, 200], [-8, 8]);
  const opacity = useTransform(x, [-220, -60, 0, 60, 220], [0, 1, 1, 1, 0]);

  function handleDragEnd(_: unknown, info: PanInfo) {
    if (Math.abs(info.offset.x) > SWIPE_THRESHOLD) {
      onDismiss();
    }
  }

  // Cards behind the top one are nudged down + scaled for a stacked look.
  const restScale = 1 - depth * 0.04;
  const restY = depth * 12;

  return (
    <motion.article
      className="card"
      style={isTop ? { x, rotate, opacity, zIndex: 10 } : { zIndex: 10 - depth }}
      initial={{ scale: restScale, y: restY + 24, opacity: 0 }}
      animate={{ scale: restScale, y: restY, opacity: 1 }}
      exit={{ x: x.get() >= 0 ? 320 : -320, opacity: 0, transition: { duration: 0.25 } }}
      transition={{ type: "spring", stiffness: 320, damping: 32 }}
      drag={isTop ? "x" : false}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.7}
      onDragEnd={handleDragEnd}
      onClick={() => isTop && setExpanded((e) => !e)}
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

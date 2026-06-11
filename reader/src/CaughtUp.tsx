import { motion } from "framer-motion";
import { type Digest } from "./digest.ts";

export function CaughtUp({
  digest,
  onReview,
}: {
  digest: Digest;
  onReview: () => void;
}) {
  const empty = digest.counts.total === 0;
  return (
    <motion.div
      className="caughtup"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="check">✓</div>
      <h2>{empty ? "Nothing new" : "You’re caught up"}</h2>
      <p className="muted">
        {empty
          ? "No fresh items since you last checked. Come back tomorrow."
          : `${digest.counts.total} item${digest.counts.total === 1 ? "" : "s"} read — ${digest.summary_line.toLowerCase()}.`}
      </p>
      {!empty && (
        <button className="review" onClick={onReview}>
          Review again
        </button>
      )}
      <p className="faint small">No more to scroll. That’s the point.</p>
    </motion.div>
  );
}

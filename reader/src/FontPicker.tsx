import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FONT_THEMES, type FontTheme, preloadAllFonts } from "./fonts.ts";

export function FontPicker({
  open,
  current,
  onPick,
  onClose,
}: {
  open: boolean;
  current: string;
  onPick: (t: FontTheme) => void;
  onClose: () => void;
}) {
  useEffect(() => {
    if (open) preloadAllFonts(); // so each row previews in its real typeface
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="sheet-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="sheet"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 38 }}
          >
            <div className="sheet-grip" />
            <div className="sheet-title">Reading font</div>
            <div className="font-list">
              {FONT_THEMES.map((t) => (
                <button
                  key={t.id}
                  className={"font-row" + (t.id === current ? " active" : "")}
                  onClick={() => onPick(t)}
                >
                  <div className="font-row-main">
                    <span
                      className="font-sample"
                      style={{ fontFamily: t.display }}
                    >
                      Claude Fable 5 released
                    </span>
                    <span className="font-meta">
                      <span className="font-name">{t.label}</span>
                      <span className="font-note faint">{t.note}</span>
                    </span>
                  </div>
                  {t.id === current && <span className="font-check">✓</span>}
                </button>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

# MOBILE.md — Flux Mobile Design Notes

## The core principle: desktop layout is opt-in

The right way to think about responsive design for a game like this is: **mobile is the default, desktop adds a sidebar**. Flux currently does the inverse — it builds a two-column desktop layout and then removes the sidebar below 700px. That works, but it means every mobile fix is fighting the default rather than going with it.

The rewrite of the responsive block in `index.html` follows this philosophy:

```css
/* Desktop: add the rail and bound the height for inner-panel scroll */
#game-screen.active { flex-direction: row; height: 100dvh; }
.game-rail { width: 320px; … }

/* Mobile: undo none of this — it was never set for mobile */
@media (max-width: 700px) {
  #game-screen { flex-direction: column; height: auto !important; overflow-y: auto; }
  .game-main   { overflow-y: visible; }
  .game-rail   { width: 100%; overflow: visible; }
}
```

---

## The bugs that were silently breaking mobile

### 1. `overflow: hidden` without a bounded height

`#game-screen { overflow: hidden }` is correct for the desktop two-panel layout — it keeps the rail from spilling outside the viewport. But without `height: 100dvh` on the game screen, there was no ceiling. Result: `.game-main { overflow-y: auto }` never triggered (nothing to scroll within), and on mobile the stacked rail was silently clipped by `overflow: hidden`.

**Fix:** `height: 100dvh` on desktop. `height: auto !important` + `overflow-y: auto` on mobile with `overflow-y: visible` on `.game-main` so the whole page scrolls naturally.

### 2. iOS Safari font-size auto-zoom

Any `<input>` focused with `font-size < 16px` causes iOS Safari to zoom the entire viewport in. The inputs were at `14px`. Once zoomed, the layout is broken until the user manually pinches out.

**Fix:** `font-size: 16px !important` on all inputs inside the mobile media query. Visually identical on a Retina display; eliminates the zoom.

### 3. Touch targets and tap delay

Buttons had no minimum height and no `touch-action`. On iOS, the 300ms synthetic-click delay is suppressed by `touch-action: manipulation`. Apple's own HIG recommends 44px minimum tap targets.

**Fix:** Added a `(hover: none) and (pointer: coarse)` block (this only fires on actual touch devices, not on a desktop browser resized to 375px):

```css
@media (hover: none) and (pointer: coarse) {
  .btn, .setting-opt, .setup-tab {
    touch-action: manipulation;
    min-height: 44px;
  }
}
```

---

## What works well already

- **Tile rack** uses `flex-wrap: wrap; justify-content: center` so 8 tiles reflow to two rows on narrow screens without overflow.
- **All overlays** are `position: fixed; inset: 0` — they cover the full viewport cleanly on mobile.
- **Lobby and game-over screens** are single-column centered layouts that need no mobile overrides.
- **Viewport meta tag** is set correctly (`width=device-width, initial-scale=1.0`).

---

## Known rough edges (ordered by impact)

### High priority

**Sticky word input.** On mobile, the word input + Submit + Pass buttons scroll off-screen as the scoreboard grows. The keyboard covers the bottom ~40% of the screen when the input is focused, so the player can't see what they're typing. A sticky bottom bar would fix this:

```css
@media (max-width: 700px) {
  .input-wrap {
    position: sticky;
    bottom: 0;
    z-index: 10;
    background: var(--bg2);
    border-top: 1px solid var(--border);
    border-radius: 0;
    padding: 12px 14px;
  }
}
```

This is the single highest-ROI mobile improvement. NYT Spelling Bee does exactly this.

**Game ID overflow.** `.game-id-display` uses `monospace; font-size: 16px; font-weight: 800`. On 320px screens the ID can overflow the card. Add `word-break: break-all` or truncate with `text-overflow: ellipsis`.

### Medium priority

**Rail order on mobile.** Chat is more time-sensitive than Board History during a game, but History appears first in the DOM (and therefore first on mobile). A CSS `order` override puts chat above history on mobile:

```css
@media (max-width: 700px) {
  .rail-chat    { order: -1; }
  .rail-history-wrap { order: 0; }
}
```

**Submitted banner + waiting pills.** The waiting pills use small `font-size: 12px` text that can be hard to tap. No action needed since they're display-only, but consider bumping to `13px` on mobile.

### Low priority

**PWA manifest.** No `manifest.json` or service worker, so the game installs as a plain browser tab rather than a home-screen app icon. For a multiplayer game where players rejoin mid-session, an installed PWA with its own icon is a meaningful UX upgrade. Minimal effort:

```json
{ "name": "Flux", "short_name": "Flux", "start_url": "/", "display": "standalone",
  "background_color": "#1e1a37", "theme_color": "#d47ae8" }
```

**`word-break` on monospace lobby URL.** The share-link box uses `overflow: hidden; text-overflow: ellipsis; white-space: nowrap` which is fine, but on very narrow screens the URL may be invisible. Already handled, just worth noting.

---

## If you wanted to go fully mobile-first

Flip the media query direction. Instead of building desktop first and overriding for mobile, write the base styles for a single-column phone layout and add the desktop sidebar with `@media (min-width: 700px)`. The CSS shrinks and you never need `!important` to undo defaults. This is a refactor, not a bug fix — the current state is functional, this is just the cleaner long-term architecture.

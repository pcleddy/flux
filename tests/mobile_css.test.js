/**
 * mobile_css.test.js
 *
 * Anti-regression tests for mobile CSS fixes.
 * Each test documents a specific bug that was found in manual testing
 * and ensures it cannot silently reappear.
 *
 * These tests parse index.html directly — no browser or build step needed.
 */

const test   = require('node:test');
const assert = require('node:assert/strict');
const fs     = require('node:fs');
const path   = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

// Pull out just the <style> block so we're not matching against HTML content
const styleMatch = html.match(/<style>([\s\S]*?)<\/style>/);
assert.ok(styleMatch, 'index.html must contain a <style> block');
const css = styleMatch[1];

// Pull out just the mobile media query block for targeted assertions.
// The block starts at @media (max-width: 700px) and ends at the matching
// closing brace. We find the opening { then walk forward counting braces.
function extractMediaBlock(src, query) {
  const start = src.indexOf(query);
  if (start === -1) return '';
  const braceOpen = src.indexOf('{', start);
  if (braceOpen === -1) return '';
  let depth = 0;
  let i = braceOpen;
  while (i < src.length) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) return src.slice(start, i + 1); }
    i++;
  }
  return '';
}
const mobileCss = extractMediaBlock(css, '@media (max-width: 700px)');


// ─── Desktop fixes ────────────────────────────────────────────────────────────

test('desktop: game screen has bounded height so inner panels can scroll', () => {
  // Bug: without height:100dvh, overflow-y:auto on .game-main never triggers
  // because #app uses min-height:100vh (not a real ceiling).
  assert.ok(
    css.includes('height: 100dvh'),
    'Expected "height: 100dvh" on #game-screen.active for inner-panel scroll to work'
  );
});


// ─── Mobile fixes (max-width: 700px) ─────────────────────────────────────────

test('mobile: game screen overrides bounded height so it can scroll as a page', () => {
  // Bug: 100dvh on mobile means all content below the fold is unreachable.
  assert.ok(
    mobileCss.includes('height: auto'),
    'Expected "height: auto" override inside @media (max-width: 700px)'
  );
});

test('mobile: game-main does not clip with overflow-y:auto when page-scrolling', () => {
  // Bug: game-main had overflow-y:auto with no ceiling, doing nothing but
  // hiding content on some browsers.
  assert.ok(
    mobileCss.includes('overflow-y: visible'),
    'Expected "overflow-y: visible" on .game-main inside mobile media query'
  );
});

test('mobile: game screen allows vertical scroll instead of clipping rail', () => {
  // Bug: overflow:hidden on #game-screen silently clipped .game-rail when
  // stacked as a column on mobile.
  assert.ok(
    mobileCss.includes('overflow-y: auto'),
    'Expected "overflow-y: auto" on #game-screen inside mobile media query'
  );
});

test('mobile: board history rail is height-capped so it does not hog the screen', () => {
  // Bug: .rail-history-wrap had flex:1 in an unconstrained column, expanding
  // to fill most of the screen as history grew.
  assert.ok(
    mobileCss.includes('max-height:') || mobileCss.includes('max-height :') ||
    css.match(/@media[^}]*max-width:\s*700px[\s\S]*?rail-history[\s\S]*?max-height/),
    'Expected max-height on .rail-history inside mobile media query'
  );
});

test('mobile: inline flex:1 is absent from rail-history-wrap element', () => {
  // Bug: inline style="flex:1" on the history card overrode the CSS override,
  // making flex:none!important ineffective.
  const inlineFlex1OnHistory = html.match(
    /rail-history-wrap[^>]*style="[^"]*flex\s*:\s*1/
  );
  assert.equal(
    inlineFlex1OnHistory,
    null,
    'Found inline flex:1 on .rail-history-wrap — this overrides the mobile CSS cap'
  );
});

test('mobile: inputs use font-size ≥ 16px to prevent iOS Safari viewport zoom', () => {
  // Bug: inputs at 14px caused iOS Safari to auto-zoom the viewport on focus,
  // breaking the layout until the user manually pinched out.
  assert.ok(
    mobileCss.includes('font-size: 16px'),
    'Expected "font-size: 16px" on inputs inside mobile media query (iOS zoom prevention)'
  );
});

test('mobile: touch targets have touch-action:manipulation to suppress 300ms delay', () => {
  // Bug: without touch-action:manipulation, iOS adds a 300ms synthetic-click
  // delay to all taps, making the game feel sluggish.
  assert.ok(
    css.includes('touch-action: manipulation'),
    'Expected "touch-action: manipulation" for touch devices'
  );
});

test('mobile: touch targets meet 44px minimum height (Apple HIG)', () => {
  assert.ok(
    css.includes('min-height: 44px'),
    'Expected "min-height: 44px" on tap targets for touch devices'
  );
});

test('mobile: word row has flex-wrap so Submit/Pass do not get squashed', () => {
  // Bug: on screens narrower than ~360px the input + Submit + Pass row
  // compressed buttons to an unusable size.
  assert.ok(
    mobileCss.includes('flex-wrap: wrap'),
    'Expected "flex-wrap: wrap" on .word-row inside mobile media query'
  );
});

test('rack: joker tile label does not inline its point value beside the icon', () => {
  assert.ok(
    !html.includes("`★${val}`"),
    'Expected joker tiles to render the icon only, with points shown in the shared value row below'
  );
});

test('setup: create screen exposes a visible Solo option', () => {
  assert.ok(
    html.includes('data-val="1">Solo</div>'),
    'Expected a visible Solo option in the max players selector'
  );
});

test('setup: create screen exposes a visible Bot opponent option', () => {
  assert.ok(
    html.includes('id="bot-mode-opts"') && html.includes('data-val="1">Bot</div>'),
    'Expected a visible Bot option in the opponent selector'
  );
});

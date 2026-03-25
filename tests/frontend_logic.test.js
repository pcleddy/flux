const test = require('node:test');
const assert = require('node:assert/strict');

const { getLettersToHighlight, buildPreviewHtml } = require('../frontend_logic.js');

const esc = (value) => String(value)
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

test('buildPreviewHtml returns good word markup for valid results', () => {
  const html = buildPreviewHtml({ status: 'valid', points: 17, message: 'Good word.' }, esc);
  assert.equal(html, '<span class="pts">Good word</span> (17 pts)');
});

test('buildPreviewHtml returns invalid markup for dictionary failures', () => {
  const html = buildPreviewHtml({ status: 'not_in_dictionary', message: 'Not a word.' }, esc);
  assert.equal(html, '<span class="invalid">Not a word.</span>');
});

test('buildPreviewHtml returns invalid markup for missing letter failures', () => {
  const html = buildPreviewHtml({ status: 'missing_letters', message: "You don't have the letters." }, esc);
  assert.equal(html, '<span class="invalid">You don\'t have the letters.</span>');
});

test('getLettersToHighlight marks rack letters used by a valid word', () => {
  const letters = getLettersToHighlight('CARS', ['C', 'A', 'R', 'T', 'S']);
  assert.deepEqual(letters.sort(), ['A', 'C', 'R', 'S']);
});

test('getLettersToHighlight includes joker for a one-family substitution', () => {
  const letters = getLettersToHighlight('BARS', ['C', 'A', 'R', 'T', 'S', '*']);
  assert.deepEqual(letters.sort(), ['*', 'A', 'R', 'S']);
});

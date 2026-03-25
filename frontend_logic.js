(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.FluxFrontendLogic = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function getLettersToHighlight(word, rack) {
    const rackSet = new Set(rack || []);
    const missingFamilies = new Set([...word].filter(ch => !rackSet.has(ch)));
    const lettersToMark = new Set([...word].filter(ch => rackSet.has(ch)));

    if (missingFamilies.size === 1 && rackSet.has('*')) {
      lettersToMark.add('*');
    }

    return [...lettersToMark];
  }

  function buildPreviewHtml(result, esc) {
    if (!result || result.status !== 'valid') {
      const message = (result && result.message) || 'Not a word.';
      return `<span class="invalid">${esc(message)}</span>`;
    }
    return `<span class="pts">Good word</span> (${result.points} pts)`;
  }

  return {
    getLettersToHighlight,
    buildPreviewHtml,
  };
});

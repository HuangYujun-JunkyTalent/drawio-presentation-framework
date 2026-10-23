// Lets the text inside a draw.io label take the label's font colour again, in the editor of the
// VS Code extension hediet.vscode-drawio.
//
// The page that the extension builds around draw.io holds the rule
//
//   .geEditor * { color: light-dark(var(--text-color), var(--dark-text-color)); }
//
// which gives every element of the editor the colour of the interface, so an element inside a
// label that sets no colour of its own, such as a `b`, a list item with its bullet, or a formula
// that MathJax draws in `currentColor`, shows black instead of the label's font colour.  The
// build and the viewer have no such rule and show the font colour.  This plugin hands the colour
// back to inheritance inside the labels of the drawing and inside the label being edited, so the
// editor shows what the build shows.  The interface of the editor keeps the rule.
//
// The VS Code extension loads the plugin from its setting "hediet.vscode-drawio.plugins", and
// asks once whether to allow it, and again after the file changes.
Draw.loadPlugin(function (ui) {
  var style = document.createElement('style');
  style.setAttribute('data-plugin', 'label-colours');
  style.textContent =
    '.geEditor .geDiagramContainer foreignObject *,' +
    '.geEditor .mxCellEditor, .geEditor .mxCellEditor * { color: inherit; }';
  document.head.appendChild(style);
  ui.editor.graph.refresh();
});

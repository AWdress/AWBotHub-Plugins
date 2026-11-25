<script setup>
// Shared presentation only. The plugin retains its own state, APIs and actions.
</script>

<template>
  <div class="aw-ios-settings"><slot /></div>
</template>

<style scoped>
.aw-ios-settings {
  --ios-surface: var(--bg-card, #fff);
  --ios-inset: var(--surface-inset, #f0f2f6);
  --ios-control: var(--bg-elevated, #fff);
  --ios-text: var(--text-primary, #1c1c1e);
  --ios-secondary: var(--text-secondary, #53555b);
  --ios-line: var(--border-card, #d5d7dd);
  --ios-accent: var(--accent-solid, #0063dc);
  --ios-accent-text: var(--accent, #0063dc);
  --ios-fast: calc(160ms * var(--glass-custom-motion, 1));
  --ios-duration: calc(260ms * var(--glass-custom-motion, 1));
  --ios-ease: var(--glass-decelerate, cubic-bezier(.22, 1, .36, 1));
  color: var(--ios-text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
  font-size: 14px;
  line-height: 1.6;
  min-width: 0;
  container-type: inline-size;
  background: transparent;
}
.aw-ios-settings :deep(*), .aw-ios-settings :deep(*::before), .aw-ios-settings :deep(*::after) { box-sizing: border-box; }
.aw-ios-settings :deep(::selection) { color: var(--ios-text); background: var(--accent-dim, #cbdfff); }
:deep(:where(button, input, textarea, select)) { font: inherit; }
.aw-ios-settings :deep(button), .aw-ios-settings :deep(summary), .aw-ios-settings :deep(a) { -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
.aw-ios-settings :deep(button) { transition: background-color var(--ios-fast) ease, color var(--ios-fast) ease, box-shadow var(--ios-fast) ease, transform var(--ios-fast) var(--ios-ease); }
.aw-ios-settings :deep(button:active:not(:disabled)) { transform: scale(calc(1 - .025 * var(--glass-custom-motion, 1))); }
.aw-ios-settings :deep(:is(button, input, textarea, select, summary, a):focus-visible) { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.aw-ios-settings :deep(:is(input, textarea, select)) { caret-color: var(--accent, #0063dc); }
.aw-ios-settings :deep(:is(input, textarea)::placeholder) { color: var(--text-placeholder, #62656d); opacity: 1; }
.aw-ios-settings :deep(:is(textarea, pre, .table-wrap)) { scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.aw-ios-settings :deep(:is(table, time, input[type=number])) { font-variant-numeric: tabular-nums; }
.aw-ios-settings :deep(select option) { background: var(--select-option-bg, var(--ios-control)); color: var(--ios-text); }
.aw-ios-settings :deep(button:disabled) { cursor: not-allowed; }
.aw-ios-settings :deep(a) { text-underline-offset: 3px; }
:global(html[data-theme="transparent"] .aw-ios-settings) {
  --ios-surface: var(--glass-surface, var(--bg-card, #171d28));
  --ios-control: var(--glass-control, var(--bg-elevated, #222b3a));
  --ios-inset: var(--glass-inset, var(--surface-inset, #111824));
}
:global(html[data-glass-motion="off"] .aw-ios-settings) { --glass-custom-motion: 0; }
:global(html[data-glass-motion="off"] .aw-ios-settings *),
:global(html[data-glass-motion="off"] .aw-ios-settings *::before),
:global(html[data-glass-motion="off"] .aw-ios-settings *::after) { transition: none !important; animation: none !important; }
:global(html[data-glass-motion="off"] .aw-ios-settings button:active:not(:disabled)) { transform: none; }
@media (prefers-reduced-motion: reduce) {
  .aw-ios-settings { --glass-custom-motion: 0; }
  .aw-ios-settings :deep(*), .aw-ios-settings :deep(*::before), .aw-ios-settings :deep(*::after) { transition: none !important; animation: none !important; scroll-behavior: auto !important; }
  .aw-ios-settings :deep(button:active:not(:disabled)) { transform: none; }
}
@media (forced-colors: active) {
  .aw-ios-settings :deep(input[type=checkbox]) { appearance: auto !important; }
}
</style>

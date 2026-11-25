<script setup>
defineProps({modelValue: Boolean, title: String, hint: String})
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="mst-switch-field">
    <span><b>{{ title }}</b><small v-if="hint">{{ hint }}</small></span>
    <input type="checkbox" role="switch" :checked="modelValue" @change="$emit('update:modelValue', $event.target.checked)">
    <i aria-hidden="true"></i>
  </label>
</template>

<style scoped>
.mst-switch-field { position:relative; display:flex; align-items:center; justify-content:space-between; gap:20px; min-height:54px; cursor:pointer; }
.mst-switch-field>span { min-width:0; }
.mst-switch-field b,.mst-switch-field small { display:block; }
.mst-switch-field b { font-size:14px; font-weight:600; line-height:1.5; }
.mst-switch-field small { margin-top:4px; color:var(--ios-secondary); font-size:12px; line-height:1.6; overflow-wrap:anywhere; }
.mst-switch-field input { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip-path:inset(50%); white-space:nowrap; border:0; }
.mst-switch-field i { position:relative; flex:0 0 50px; width:50px; height:30px; border-radius:15px; background:var(--switch-bg,var(--ios-line)); pointer-events:none; transition:background-color var(--ios-fast) ease; }
.mst-switch-field i::after { content:""; position:absolute; inset-inline-start:3px; top:3px; width:24px; height:24px; border-radius:50%; background:var(--switch-thumb,#fff); box-shadow:0 2px 4px rgba(0,0,0,.15); transition:transform var(--ios-duration) var(--ios-ease); }
.mst-switch-field input:checked+i { background:var(--success,#178a45); }
.mst-switch-field input:checked+i::after { transform:translateX(20px); }
.mst-switch-field:has(input:focus-visible) i { outline:3px solid var(--ios-accent-text); outline-offset:3px; }
.mst-switch-field:has(input:disabled) { cursor:not-allowed; opacity:.48; }
@media(forced-colors:active) {
  .mst-switch-field input { position:static; width:24px; height:24px; margin:0; clip-path:none; }
  .mst-switch-field i { display:none; }
}
</style>

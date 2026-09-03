<script setup lang="ts">
import type { ToastItem } from "../composables/useToast";
import type { Lang } from "../i18n";

defineProps<{
  toasts: ToastItem[];
  language: Lang;
}>();

const emit = defineEmits<{
  (e: "dismiss", id: string): void;
}>();
</script>

<template>
  <div
    v-if="toasts.length > 0"
    class="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 pointer-events-none"
    role="status"
    aria-live="polite"
    aria-atomic="false"
  >
    <button
      v-for="toast in toasts"
      :key="toast.id"
      type="button"
      class="pointer-events-auto flex items-center gap-3 px-4 py-3 bg-monokai-light-card/95 dark:bg-monokai-panel/95 border border-monokai-light-border dark:border-monokai-border shadow-xl backdrop-blur-md rounded-2xl text-xs font-semibold text-monokai-light-fg dark:text-monokai-fg transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] cursor-pointer text-left"
      :aria-label="
        toast.title +
        (toast.message ? ': ' + toast.message : '') +
        ' — ' +
        (language === 'de' ? 'Klicken zum Schließen' : 'Click to dismiss')
      "
      @click="emit('dismiss', toast.id)"
    >
      <span
        class="w-2 h-2 rounded-full shrink-0"
        :class="{
          'bg-emerald-500': toast.type === 'success',
          'bg-blue-500': toast.type === 'info',
          'bg-rose-500': toast.type === 'error',
        }"
      />
      <div>
        <p class="font-bold">{{ toast.title }}</p>
        <p
          v-if="toast.message"
          class="text-slate-500 dark:text-monokai-muted font-normal text-[11px]"
        >
          {{ toast.message }}
        </p>
      </div>
    </button>
  </div>
</template>

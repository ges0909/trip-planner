<script setup lang="ts">
import { AlertTriangle } from "@lucide/vue";
import { nextTick, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    message?: string;
    confirmText?: string;
    cancelText?: string;
    confirmButtonClass?: string;
  }>(),
  {
    message: "",
    confirmText: "Bestätigen",
    cancelText: "Abbrechen",
    confirmButtonClass:
      "px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500",
  },
);

const emit = defineEmits<{
  (e: "confirm"): void;
  (e: "cancel"): void;
  (e: "update:open", val: boolean): void;
}>();

const dialogRef = ref<HTMLElement | null>(null);
const cancelBtnRef = ref<HTMLButtonElement | null>(null);

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      await nextTick();
      cancelBtnRef.value?.focus();
    }
  },
);

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    emit("cancel");
    emit("update:open", false);
    return;
  }

  if (e.key === "Tab" && dialogRef.value) {
    const focusable = dialogRef.value.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs"
      @click.self="
        emit('cancel');
        emit('update:open', false);
      "
    >
      <div
        ref="dialogRef"
        class="relative w-full max-w-sm overflow-hidden rounded-2xl bg-white p-6 shadow-2xl border border-gray-100 animate-in fade-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        @keydown="handleKeydown"
      >
        <div class="flex items-start gap-4">
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600"
          >
            <AlertTriangle :size="20" aria-hidden="true" />
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="text-base font-semibold text-gray-900">
              {{ title }}
            </h3>
            <p v-if="message" class="mt-1.5 text-sm text-gray-600 leading-relaxed break-words">
              {{ message }}
            </p>
            <slot />
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-2.5">
          <button
            ref="cancelBtnRef"
            type="button"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-400"
            @click="
              emit('cancel');
              emit('update:open', false);
            "
          >
            {{ cancelText }}
          </button>
          <button type="button" :class="confirmButtonClass" @click="emit('confirm')">
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

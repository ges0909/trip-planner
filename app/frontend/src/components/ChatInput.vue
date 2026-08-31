<script setup lang="ts">
import { ArrowRight, LoaderCircle, Square } from "@lucide/vue";
import { ref } from "vue";
import { t, type Lang } from "../i18n";

const props = defineProps<{
  isLoading: boolean;
  language: Lang;
}>();
const emit = defineEmits<{ send: [message: string]; cancel: [] }>();

const input = ref("");

function handleSubmit() {
  const message = input.value.trim();
  if (!message) return;
  emit("send", message);
}

function clear() {
  input.value = "";
}

defineExpose({ clear });
</script>

<template>
  <div class="relative">
    <form @submit.prevent="handleSubmit">
      <div
        class="relative flex items-center bg-monokai-light-card dark:bg-monokai-card rounded-2xl border border-monokai-light-border dark:border-monokai-border shadow-xs hover:shadow-md focus-within:border-blue-500 dark:focus-within:border-monokai-cyan focus-within:ring-4 focus-within:ring-blue-500/10 transition-all duration-200"
      >
        <textarea
          v-model="input"
          :disabled="isLoading"
          :placeholder="t('placeholder', props.language)"
          rows="2"
          class="w-full px-4 py-3 pr-24 border-0 rounded-2xl focus:outline-none bg-transparent disabled:opacity-50 resize-none text-base text-monokai-light-fg dark:text-monokai-fg placeholder-monokai-light-muted dark:placeholder-monokai-muted"
          @keydown.enter.exact.prevent="handleSubmit"
        />
        <div class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
          <button
            v-if="isLoading"
            type="button"
            class="p-2 bg-slate-700 dark:bg-monokai-panel text-white dark:text-monokai-fg border border-slate-600 dark:border-monokai-border rounded-xl hover:bg-slate-800 transition shadow-xs cursor-pointer"
            :title="t('cancel', props.language)"
            :aria-label="t('cancel', props.language)"
            @click="emit('cancel')"
          >
            <Square :size="16" aria-hidden="true" />
          </button>
          <button
            type="submit"
            :disabled="isLoading || !input.trim()"
            :class="[
              'p-2.5 rounded-xl transition flex items-center justify-center',
              isLoading || !input.trim()
                ? 'bg-slate-200 dark:bg-monokai-panel text-slate-400 dark:text-monokai-muted cursor-not-allowed opacity-60'
                : 'bg-blue-600 dark:bg-monokai-cyan text-white dark:text-monokai-bg hover:bg-blue-700 dark:hover:bg-sky-300 shadow-md cursor-pointer font-bold',
            ]"
            :title="t('btnSend', props.language)"
            :aria-label="t('btnSend', props.language)"
          >
            <LoaderCircle v-if="isLoading" :size="17" class="animate-spin" aria-hidden="true" />
            <ArrowRight v-else :size="17" aria-hidden="true" />
            <span class="sr-only">{{ t("btnSend", props.language) }}</span>
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

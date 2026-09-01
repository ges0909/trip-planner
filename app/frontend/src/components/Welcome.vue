<script setup lang="ts">
import { ChevronRight, Sparkles } from "@lucide/vue";
import { computed } from "vue";
import { getPromptSuggestions } from "../config/suggestions";
import type { Lang } from "../i18n";

const props = defineProps<{
  language: Lang;
  isLoading: boolean;
}>();

const emit = defineEmits<{
  (e: "selectPrompt", prompt: string): void;
}>();

const promptSuggestions = computed(() => getPromptSuggestions(props.language));
</script>

<template>
  <div v-if="!isLoading" class="py-10 px-4 max-w-4xl mx-auto text-center">
    <div
      class="inline-flex items-center justify-center p-3.5 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-monokai-card dark:to-monokai-panel text-blue-600 dark:text-monokai-yellow rounded-2xl mb-4 shadow-xs border border-blue-100 dark:border-monokai-border"
    >
      <Sparkles :size="28" aria-hidden="true" />
    </div>
    <h2 class="text-2xl font-bold text-slate-800 dark:text-monokai-fg sm:text-3xl tracking-tight">
      {{
        language === "de" ? "Wohin führt dein nächstes Abenteuer?" : "Where is your next adventure?"
      }}
    </h2>
    <p class="mt-2 text-slate-500 dark:text-monokai-muted text-sm max-w-lg mx-auto">
      {{
        language === "de"
          ? "Erstelle maßgeschneiderte Radtouren und Roadtrips mit KI-Unterstützung, Routenkarten und GPX-Export."
          : "Create tailored bike tours and road trips with AI assistance, route maps, and GPX export."
      }}
    </p>

    <div class="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
      <button
        v-for="suggestion in promptSuggestions"
        :key="suggestion.title"
        type="button"
        class="group p-4 bg-white dark:bg-monokai-card border border-monokai-light-border dark:border-monokai-border rounded-2xl hover:border-blue-500 dark:hover:border-monokai-yellow hover:shadow-md transition-all text-left flex flex-col justify-between focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 cursor-pointer"
        @click="emit('selectPrompt', suggestion.prompt)"
      >
        <div>
          <div class="flex items-center justify-between">
            <span class="text-2xl">{{ suggestion.emoji }}</span>
            <span
              class="text-xs font-semibold px-2 py-0.5 rounded-full"
              :class="suggestion.badgeClass"
            >
              {{ suggestion.tag }}
            </span>
          </div>
          <h3
            class="mt-3 font-semibold text-slate-800 dark:text-monokai-fg text-sm group-hover:text-blue-600 dark:group-hover:text-monokai-cyan transition"
          >
            {{ suggestion.title }}
          </h3>
          <p class="mt-1 text-xs text-slate-500 dark:text-monokai-muted line-clamp-2">
            {{ suggestion.prompt }}
          </p>
        </div>
        <div
          class="mt-4 flex items-center text-xs font-semibold text-blue-600 dark:text-monokai-cyan opacity-0 group-hover:opacity-100 transition"
        >
          <span>{{ language === "de" ? "Tour planen" : "Plan tour" }}</span>
          <ChevronRight :size="14" class="ml-1" />
        </div>
      </button>
    </div>
  </div>
</template>

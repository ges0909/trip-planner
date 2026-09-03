<script setup lang="ts">
import { Compass, FolderHeart, Moon, Search, Sun } from "@lucide/vue";
import type { Lang } from "../i18n";
import LanguageSelector from "./LanguageSelector.vue";
import SessionHistory from "./SessionHistory.vue";

defineProps<{
  language: Lang;
  isDark: boolean;
  isLoading: boolean;
  activeSessionId: string | null;
  isLibraryOpen?: boolean;
}>();

const emit = defineEmits<{
  (e: "resetSession"): void;
  (e: "openSearch"): void;
  (e: "update:language", val: Lang): void;
  (e: "toggleTheme"): void;
  (e: "selectSession", sessionId: string): void;
  (e: "sessionsCleared"): void;
  (e: "toggleLibrary"): void;
}>();
</script>

<template>
  <header
    class="border-b border-monokai-light-border dark:border-monokai-border bg-monokai-light-card/80 dark:bg-monokai-card/80 backdrop-blur-md sticky top-0 z-30 transition-colors"
  >
    <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
      <!-- Left: Logo & Title (clickable to return home) -->
      <button
        type="button"
        class="flex items-center gap-3 cursor-pointer group focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 rounded-xl"
        :title="language === 'de' ? 'Zurück zur Startseite' : 'Return to main page'"
        @click="emit('resetSession')"
      >
        <div
          class="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 dark:from-monokai-yellow dark:to-amber-500 text-white dark:text-slate-950 rounded-xl shadow-xs group-hover:scale-105 transition-transform"
        >
          <Compass :size="22" aria-hidden="true" />
        </div>
        <div class="text-left">
          <h1
            class="text-lg font-bold text-slate-800 dark:text-monokai-fg tracking-tight leading-tight group-hover:text-blue-600 dark:group-hover:text-monokai-cyan transition-colors"
          >
            Tour Pilot
          </h1>
          <p class="text-[11px] font-medium text-slate-400 dark:text-monokai-muted hidden sm:block">
            {{ language === "de" ? "AI Route Planner" : "AI Route Planner" }}
          </p>
        </div>
      </button>

      <!-- Right: Library, Search, Chat History, Language & Theme Controls -->
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="h-9 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-monokai-light-fg dark:text-monokai-fg bg-monokai-light-card dark:bg-monokai-card hover:bg-monokai-light-panel dark:hover:bg-monokai-panel border border-monokai-light-border dark:border-monokai-border rounded-xl shadow-xs transition-all cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
          :class="
            isLibraryOpen
              ? 'border-blue-300 dark:border-monokai-purple/50 bg-blue-50/50 dark:bg-monokai-panel'
              : ''
          "
          :title="
            isLibraryOpen
              ? language === 'de'
                ? 'Bibliothek einklappen'
                : 'Collapse library'
              : language === 'de'
                ? 'Bibliothek öffnen'
                : 'Open library'
          "
          @click="emit('toggleLibrary')"
        >
          <FolderHeart
            :size="15"
            class="text-blue-600 dark:text-monokai-purple"
            aria-hidden="true"
          />
          <span class="hidden sm:inline">{{ language === "de" ? "Bibliothek" : "Library" }}</span>
        </button>

        <button
          type="button"
          class="h-9 inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-monokai-light-fg dark:text-monokai-fg bg-monokai-light-card dark:bg-monokai-card hover:bg-monokai-light-panel dark:hover:bg-monokai-panel border border-monokai-light-border dark:border-monokai-border rounded-xl shadow-xs transition-all cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
          :title="language === 'de' ? 'Suche öffnen (⌘K)' : 'Open search (⌘K)'"
          @click="emit('openSearch')"
        >
          <Search :size="14" aria-hidden="true" />
          <span class="hidden md:inline">{{ language === "de" ? "Suchen..." : "Search..." }}</span>
          <kbd
            class="hidden lg:inline-block text-[10px] bg-monokai-light-panel dark:bg-monokai-panel px-1.5 py-0.5 rounded-md border border-monokai-light-border dark:border-monokai-border text-monokai-light-muted dark:text-monokai-muted"
            >⌘K</kbd
          >
        </button>

        <SessionHistory
          :language="language"
          :is-loading="isLoading"
          :active-session-id="activeSessionId"
          @select="(id: string) => emit('selectSession', id)"
          @cleared="emit('sessionsCleared')"
        />

        <LanguageSelector
          :model-value="language"
          @update:model-value="(val: Lang) => emit('update:language', val)"
        />

        <button
          type="button"
          class="h-9 inline-flex items-center justify-center p-2 text-xs font-semibold text-monokai-light-fg dark:text-monokai-fg bg-monokai-light-card dark:bg-monokai-card hover:bg-monokai-light-panel dark:hover:bg-monokai-panel border border-monokai-light-border dark:border-monokai-border rounded-xl shadow-xs transition-all cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
          :title="language === 'de' ? 'Farbschema umschalten' : 'Toggle color theme'"
          @click="emit('toggleTheme')"
        >
          <Sun v-if="isDark" :size="16" class="text-monokai-yellow" aria-hidden="true" />
          <Moon v-else :size="16" class="text-slate-600" aria-hidden="true" />
        </button>
      </div>
    </div>
  </header>
</template>

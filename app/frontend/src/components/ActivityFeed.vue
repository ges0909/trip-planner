<script setup lang="ts">
import { ChevronDown, ChevronRight } from "@lucide/vue";
import type { ActivityEvent } from "../composables/useChat";
import { t, type Lang } from "../i18n";

defineProps<{
  events: ActivityEvent[];
  isLoading: boolean;
  language: Lang;
  isExpanded: boolean;
}>();

const emit = defineEmits<{
  (e: "toggleExpanded"): void;
}>();
</script>

<template>
  <div
    v-if="events.length > 0"
    class="mt-3 bg-blue-50/80 dark:bg-monokai-card/90 border border-blue-100 dark:border-monokai-border rounded-xl overflow-hidden transition-all shadow-xs"
  >
    <button
      type="button"
      class="w-full px-3.5 py-2.5 flex items-center justify-between gap-3 text-left hover:bg-blue-100/50 dark:hover:bg-monokai-panel/50 transition cursor-pointer"
      @click="emit('toggleExpanded')"
    >
      <div class="flex items-center gap-2">
        <span class="flex h-2 w-2 relative">
          <span
            v-if="isLoading"
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"
          ></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
        </span>
        <span class="text-xs font-semibold text-blue-900 dark:text-monokai-fg">
          {{
            isLoading
              ? language === "de"
                ? "KI erstellt deine Route..."
                : "AI is crafting your tour..."
              : language === "de"
                ? `Aktivitätsverlauf (${events.length})`
                : `Activity History (${events.length})`
          }}
        </span>
      </div>

      <div class="flex items-center gap-2">
        <span
          v-if="isLoading"
          class="text-[11px] text-blue-600 dark:text-monokai-yellow animate-pulse font-medium"
        >
          {{ language === "de" ? "Wird verarbeitet..." : "Processing..." }}
        </span>
        <component
          :is="isExpanded ? ChevronDown : ChevronRight"
          :size="15"
          class="text-blue-500 dark:text-monokai-muted"
        />
      </div>
    </button>

    <!-- Expanded Event Stream List -->
    <div
      v-show="isExpanded"
      class="px-3.5 pb-3 pt-1 border-t border-blue-100/60 dark:border-monokai-border space-y-1.5 max-h-64 overflow-y-auto scrollbar-thin"
    >
      <p
        v-for="(event, index) in events"
        :key="index"
        class="text-xs text-blue-800 dark:text-monokai-cyan font-mono flex items-start gap-2"
      >
        <span
          class="inline-block w-1.5 h-1.5 rounded-full bg-monokai-yellow shrink-0 mt-1.5"
        ></span>
        <span class="break-words">
          <template v-if="event.type === 'model'">
            {{
              t("modelCall", language, {
                iteration: event.iteration,
                modelId: event.modelId,
              })
            }}
          </template>
          <template v-else-if="event.type === 'tool'">
            {{ t("toolCall", language, { name: event.name }) }}
          </template>
          <template v-else>{{ event.message }}</template>
        </span>
      </p>
    </div>
  </div>
</template>

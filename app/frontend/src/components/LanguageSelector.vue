<script setup lang="ts">
import { Check, ChevronDown } from "@lucide/vue";
import { computed, onMounted, onUnmounted, ref } from "vue";
import type { Lang } from "../i18n";

const props = defineProps<{
  modelValue: Lang;
}>();

const emit = defineEmits<{
  "update:modelValue": [lang: Lang];
}>();

const isOpen = ref(false);
const containerRef = ref<HTMLElement | null>(null);

const languages: { code: Lang; label: string }[] = [
  { code: "de", label: "Deutsch" },
  { code: "en", label: "English" },
];

const currentLanguage = computed(
  () => languages.find((l) => l.code === props.modelValue) || languages[0],
);

function selectLanguage(lang: Lang) {
  emit("update:modelValue", lang);
  isOpen.value = false;
}

function handleClickOutside(e: MouseEvent) {
  if (isOpen.value && containerRef.value && !containerRef.value.contains(e.target as Node)) {
    isOpen.value = false;
  }
}

// #8 Escape closes the dropdown
function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && isOpen.value) {
    isOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
  document.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
  document.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <div ref="containerRef" class="relative">
    <button
      type="button"
      class="inline-flex items-center gap-2 h-9 px-3 text-xs font-medium rounded-xl border border-monokai-light-border dark:border-monokai-border bg-monokai-light-card dark:bg-monokai-card text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/50 transition cursor-pointer shadow-xs"
      title="Sprache auswählen / Choose language"
      aria-label="Sprache auswählen / Choose language"
      :aria-expanded="isOpen"
      :aria-haspopup="true"
      @click="isOpen = !isOpen"
    >
      <!-- German Flag SVG -->
      <svg
        v-if="currentLanguage.code === 'de'"
        class="h-3.5 w-5 rounded-xs overflow-hidden shadow-xs shrink-0 border border-gray-300"
        viewBox="0 0 5 3"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <rect width="5" height="1" y="0" fill="#000000" />
        <rect width="5" height="1" y="1" fill="#DD0000" />
        <rect width="5" height="1" y="2" fill="#FFCE00" />
      </svg>
      <!-- US Flag SVG -->
      <svg
        v-else
        class="h-3.5 w-5 rounded-xs overflow-hidden shadow-xs shrink-0 border border-gray-300"
        viewBox="0 0 741 390"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <rect width="741" height="390" fill="#B22234" />
        <path
          d="M0,30H741M0,90H741M0,150H741M0,210H741M0,270H741M0,330H741"
          stroke="#fff"
          stroke-width="30"
        />
        <rect width="296" height="210" fill="#3C3B6E" />
        <g fill="#fff">
          <g id="us-star-btn">
            <polygon points="25,18 28,26 36,26 30,31 32,39 25,34 18,39 20,31 14,26 22,26" />
          </g>
          <use href="#us-star-btn" x="48" />
          <use href="#us-star-btn" x="96" />
          <use href="#us-star-btn" x="144" />
          <use href="#us-star-btn" x="192" />
          <use href="#us-star-btn" x="240" />
          <use href="#us-star-btn" x="24" y="32" />
          <use href="#us-star-btn" x="72" y="32" />
          <use href="#us-star-btn" x="120" y="32" />
          <use href="#us-star-btn" x="168" y="32" />
          <use href="#us-star-btn" x="216" y="32" />
          <use href="#us-star-btn" y="64" />
          <use href="#us-star-btn" x="48" y="64" />
          <use href="#us-star-btn" x="96" y="64" />
          <use href="#us-star-btn" x="144" y="64" />
          <use href="#us-star-btn" x="192" y="64" />
          <use href="#us-star-btn" x="240" y="64" />
          <use href="#us-star-btn" x="24" y="96" />
          <use href="#us-star-btn" x="72" y="96" />
          <use href="#us-star-btn" x="120" y="96" />
          <use href="#us-star-btn" x="168" y="96" />
          <use href="#us-star-btn" x="216" y="96" />
          <use href="#us-star-btn" y="128" />
          <use href="#us-star-btn" x="48" y="128" />
          <use href="#us-star-btn" x="96" y="128" />
          <use href="#us-star-btn" x="144" y="128" />
          <use href="#us-star-btn" x="192" y="128" />
          <use href="#us-star-btn" x="240" y="128" />
        </g>
      </svg>
      <span class="font-semibold text-xs uppercase text-monokai-light-fg dark:text-monokai-fg">{{
        currentLanguage.code.toUpperCase()
      }}</span>
      <ChevronDown
        :size="13"
        class="text-monokai-light-muted dark:text-monokai-muted"
        aria-hidden="true"
      />
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 z-20 mt-2 w-40 overflow-hidden rounded-xl border border-monokai-light-border dark:border-monokai-border bg-monokai-light-panel dark:bg-monokai-panel shadow-xl py-1"
    >
      <button
        v-for="lang in languages"
        :key="lang.code"
        type="button"
        class="flex w-full items-center justify-between px-3 py-2 text-left text-xs transition font-medium"
        :class="
          props.modelValue === lang.code
            ? 'font-bold text-blue-600 dark:text-monokai-cyan bg-blue-50/70 dark:bg-monokai-card'
            : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-card dark:hover:bg-monokai-card/60'
        "
        @click="selectLanguage(lang.code)"
      >
        <span class="flex items-center gap-2.5">
          <!-- German Flag SVG -->
          <svg
            v-if="lang.code === 'de'"
            class="h-3.5 w-5 rounded-xs overflow-hidden shadow-xs shrink-0 border border-gray-300"
            viewBox="0 0 5 3"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <rect width="5" height="1" y="0" fill="#000000" />
            <rect width="5" height="1" y="1" fill="#DD0000" />
            <rect width="5" height="1" y="2" fill="#FFCE00" />
          </svg>
          <!-- US Flag SVG -->
          <svg
            v-else
            class="h-3.5 w-5 rounded-xs overflow-hidden shadow-xs shrink-0 border border-gray-300"
            viewBox="0 0 741 390"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <rect width="741" height="390" fill="#B22234" />
            <path
              d="M0,30H741M0,90H741M0,150H741M0,210H741M0,270H741M0,330H741"
              stroke="#fff"
              stroke-width="30"
            />
            <rect width="296" height="210" fill="#3C3B6E" />
            <g fill="#fff">
              <g id="us-star-menu">
                <polygon points="25,18 28,26 36,26 30,31 32,39 25,34 18,39 20,31 14,26 22,26" />
              </g>
              <use href="#us-star-menu" x="48" />
              <use href="#us-star-menu" x="96" />
              <use href="#us-star-menu" x="144" />
              <use href="#us-star-menu" x="192" />
              <use href="#us-star-menu" x="240" />
              <use href="#us-star-menu" x="24" y="32" />
              <use href="#us-star-menu" x="72" y="32" />
              <use href="#us-star-menu" x="120" y="32" />
              <use href="#us-star-menu" x="168" y="32" />
              <use href="#us-star-menu" x="216" y="32" />
              <use href="#us-star-menu" y="64" />
              <use href="#us-star-menu" x="48" y="64" />
              <use href="#us-star-menu" x="96" y="64" />
              <use href="#us-star-menu" x="144" y="64" />
              <use href="#us-star-menu" x="192" y="64" />
              <use href="#us-star-menu" x="240" y="64" />
              <use href="#us-star-menu" x="24" y="96" />
              <use href="#us-star-menu" x="72" y="96" />
              <use href="#us-star-menu" x="120" y="96" />
              <use href="#us-star-menu" x="168" y="96" />
              <use href="#us-star-menu" x="216" y="96" />
              <use href="#us-star-menu" y="128" />
              <use href="#us-star-menu" x="48" y="128" />
              <use href="#us-star-menu" x="96" y="128" />
              <use href="#us-star-menu" x="144" y="128" />
              <use href="#us-star-menu" x="192" y="128" />
              <use href="#us-star-menu" x="240" y="128" />
            </g>
          </svg>
          <span>{{ lang.label }}</span>
        </span>
        <Check
          v-if="props.modelValue === lang.code"
          :size="15"
          class="text-blue-600"
          aria-hidden="true"
        />
      </button>
    </div>
  </div>
</template>

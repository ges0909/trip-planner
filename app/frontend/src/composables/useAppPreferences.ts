import { ref, watch } from "vue";
import type { Lang } from "../i18n";

export function useAppPreferences() {
  const detectLanguage = (): Lang => {
    const stored = localStorage.getItem("tourpilot_lang");
    if (stored === "de" || stored === "en") return stored;

    const browser = navigator.language.slice(0, 2).toLowerCase();
    return browser === "en" ? "en" : "de";
  };

  const language = ref<Lang>(detectLanguage());

  const setLanguage = (lang: Lang) => {
    language.value = lang;
    localStorage.setItem("tourpilot_lang", lang);
  };

  const detectDark = (): boolean => {
    const stored = localStorage.getItem("tourpilot_theme");
    if (stored === "dark") return true;
    if (stored === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  };

  const isDark = ref(detectDark());

  const updateDarkClass = () => {
    document.documentElement.classList.toggle("dark", isDark.value);
  };

  const toggleTheme = () => {
    isDark.value = !isDark.value;
    localStorage.setItem("tourpilot_theme", isDark.value ? "dark" : "light");
    updateDarkClass();
  };

  watch(
    isDark,
    () => {
      updateDarkClass();
    },
    { immediate: true },
  );

  return {
    language,
    isDark,
    setLanguage,
    toggleTheme,
    detectLanguage,
    detectDark,
    updateDarkClass,
  };
}

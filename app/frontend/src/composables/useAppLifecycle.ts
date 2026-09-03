import { onMounted, onUnmounted, ref } from "vue";

export function useAppLifecycle(options: {
  onToggleMap: () => void;
  onInitializeSession: () => Promise<void>;
  onEscape?: () => void;
}) {
  const isOnline = ref(navigator.onLine);

  function handleOnline() {
    isOnline.value = true;
  }

  function handleOffline() {
    isOnline.value = false;
  }

  function handleGlobalKeydown(e: KeyboardEvent) {
    const target = e.target as HTMLElement | null;
    const isInput =
      target &&
      (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

    if (isInput) return;

    if (e.key === "Escape") {
      if (options.onEscape) {
        e.preventDefault();
        options.onEscape();
      }
      return;
    }

    if (e.key === "m" || e.key === "M") {
      if (!e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        options.onToggleMap();
      }
    }
  }

  onMounted(() => {
    void options.onInitializeSession();
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    window.addEventListener("keydown", handleGlobalKeydown);
  });

  onUnmounted(() => {
    window.removeEventListener("online", handleOnline);
    window.removeEventListener("offline", handleOffline);
    window.removeEventListener("keydown", handleGlobalKeydown);
  });

  return { isOnline };
}

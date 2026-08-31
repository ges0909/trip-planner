import { ref } from "vue";

export interface ToastItem {
  id: string;
  type: "success" | "info" | "error";
  title: string;
  message?: string;
}

const toasts = ref<ToastItem[]>([]);

export function useToast() {
  function addToast(
    title: string,
    message?: string,
    type: ToastItem["type"] = "success",
    duration = 3000,
  ) {
    const id = "toast-" + Date.now() + "-" + Math.random().toString(36).slice(2, 7);
    const item: ToastItem = { id, type, title, message };
    toasts.value.push(item);

    setTimeout(() => {
      removeToast(id);
    }, duration);
  }

  function removeToast(id: string) {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }

  return {
    toasts,
    addToast,
    removeToast,
  };
}

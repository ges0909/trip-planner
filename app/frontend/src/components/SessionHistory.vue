<script setup lang="ts">
import { AlertTriangle, History, Trash2 } from "@lucide/vue";
import { nextTick, onMounted, onUnmounted, ref } from "vue";
import { deleteAllSessions, deleteSession, fetchSessions, type Session } from "../api";
import { t, type Lang } from "../i18n";

const props = defineProps<{
  language: Lang;
  isLoading: boolean;
  activeSessionId?: string | null;
}>();

const emit = defineEmits<{
  select: [sessionId: string];
  deleted: [sessionId: string];
  cleared: [];
}>();

const sessions = ref<Session[]>([]);
const isOpen = ref(false);
const error = ref("");
const containerRef = ref<HTMLElement | null>(null);

// #3 Focus-trap refs
const dialogRef = ref<HTMLElement | null>(null);
const cancelBtnRef = ref<HTMLButtonElement | null>(null);

const confirmDialog = ref<{
  open: boolean;
  type: "single" | "all";
  sessionId?: string;
  title?: string | null;
}>({
  open: false,
  type: "single",
});

async function loadSessions() {
  error.value = "";
  try {
    sessions.value = await fetchSessions();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load sessions";
  }
}

async function toggle() {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    await loadSessions();
  }
}

function select(session: Session) {
  isOpen.value = false;
  emit("select", session.id);
}

async function requestDeleteSession(sessionId: string, title?: string | null) {
  confirmDialog.value = { open: true, type: "single", sessionId, title };
  await nextTick();
  cancelBtnRef.value?.focus();
}

async function requestClearAll() {
  confirmDialog.value = { open: true, type: "all" };
  await nextTick();
  cancelBtnRef.value?.focus();
}

async function handleConfirmDelete() {
  if (confirmDialog.value.type === "single" && confirmDialog.value.sessionId) {
    const id = confirmDialog.value.sessionId;
    confirmDialog.value.open = false;
    try {
      await deleteSession(id);
      sessions.value = sessions.value.filter((s) => s.id !== id);
      emit("deleted", id);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Failed to delete session";
    }
  } else if (confirmDialog.value.type === "all") {
    confirmDialog.value.open = false;
    try {
      await deleteAllSessions();
      sessions.value = [];
      emit("cleared");
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Failed to clear sessions";
    }
  }
}

// #3 Focus-trap: keep Tab/Shift+Tab inside the dialog, Escape closes it
function handleDialogKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    confirmDialog.value.open = false;
    return;
  }
  if (e.key !== "Tab") return;
  const dialog = dialogRef.value;
  if (!dialog) return;
  const focusable = Array.from(
    dialog.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => !el.hasAttribute("disabled"));
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  } else {
    if (document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

function handleClickOutside(e: MouseEvent) {
  if (isOpen.value && containerRef.value && !containerRef.value.contains(e.target as Node)) {
    if (!confirmDialog.value.open) {
      isOpen.value = false;
    }
  }
}

// #8 Escape closes the dropdown
function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && isOpen.value && !confirmDialog.value.open) {
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

function formatDate(value: string, language: Lang) {
  return new Date(value).toLocaleDateString(language === "de" ? "de-DE" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<template>
  <div ref="containerRef" class="relative">
    <button
      type="button"
      class="inline-flex items-center gap-2 h-9 px-3 text-xs font-medium rounded-xl border border-monokai-light-border dark:border-monokai-border bg-monokai-light-card dark:bg-monokai-card text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/50 transition cursor-pointer shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
      :title="t('sessionHistory', language)"
      :aria-label="t('sessionHistory', language)"
      :aria-expanded="isOpen"
      :aria-haspopup="true"
      @click="toggle"
    >
      <History :size="15" aria-hidden="true" class="text-emerald-600 dark:text-monokai-green" />
      <span>{{ t("sessionHistory", language) }}</span>
    </button>

    <div
      v-if="isOpen"
      role="menu"
      class="absolute right-0 z-20 mt-2 w-80 sm:w-96 overflow-hidden rounded-xl border border-monokai-light-border dark:border-monokai-border bg-monokai-light-panel dark:bg-monokai-panel shadow-xl"
    >
      <div
        v-if="error"
        role="alert"
        class="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400"
      >
        {{ error }}
      </div>
      <div
        v-else-if="sessions.length === 0"
        class="p-4 text-sm text-monokai-light-muted dark:text-monokai-muted text-center"
      >
        {{ t("noSessions", language) }}
      </div>
      <div v-else>
        <div
          class="max-h-80 overflow-y-auto divide-y divide-monokai-light-border dark:divide-monokai-border"
        >
          <div
            v-for="session in sessions"
            :key="session.id"
            :class="[
              'group flex items-center justify-between px-3.5 py-2.5 text-left hover:bg-monokai-light-card dark:hover:bg-monokai-bg/60 transition',
              props.activeSessionId === session.id ? 'bg-blue-50/70 dark:bg-monokai-cyan/10' : '',
            ]"
          >
            <button
              type="button"
              role="menuitem"
              :disabled="isLoading"
              class="flex-1 min-w-0 pr-2 text-left disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500 rounded"
              @click="select(session)"
            >
              <span
                class="block truncate text-sm font-medium text-monokai-light-fg dark:text-monokai-fg group-hover:text-blue-600 dark:group-hover:text-monokai-cyan"
              >
                {{ session.title || t("loadSession", language) }}
              </span>
              <span class="mt-0.5 block text-xs text-monokai-light-muted dark:text-monokai-muted">
                {{ formatDate(session.updated_at, language) }} · {{ session.tour_type || "–" }}
              </span>
            </button>
            <button
              type="button"
              :disabled="isLoading"
              class="shrink-0 p-1.5 text-monokai-light-muted dark:text-monokai-muted hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/30 transition opacity-0 group-hover:opacity-100 focus:opacity-100 focus-visible:opacity-100 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-red-500"
              :title="t('deleteSession', language)"
              :aria-label="t('deleteSession', language) + ': ' + (session.title || session.id)"
              @click.stop.prevent="requestDeleteSession(session.id, session.title)"
            >
              <Trash2 :size="14" aria-hidden="true" />
            </button>
          </div>
        </div>
        <div
          class="border-t border-monokai-light-border dark:border-monokai-border bg-monokai-light-card/50 dark:bg-monokai-bg/40 p-2"
        >
          <button
            type="button"
            :disabled="isLoading"
            class="flex items-center justify-center gap-1.5 w-full rounded-lg px-2 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition font-medium disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-red-500"
            @click="requestClearAll"
          >
            <Trash2 :size="13" aria-hidden="true" />
            <span>{{ t("clearAllSessions", language) }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- #3 Confirmation Modal with focus-trap -->
    <Teleport to="body">
      <div
        v-if="confirmDialog.open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs"
        @click.self="confirmDialog.open = false"
      >
        <div
          ref="dialogRef"
          class="relative w-full max-w-sm overflow-hidden rounded-2xl bg-white p-6 shadow-2xl border border-gray-100 animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="'dialog-title-session'"
          @keydown="handleDialogKeydown"
        >
          <div class="flex items-start gap-4">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600"
            >
              <AlertTriangle :size="20" aria-hidden="true" />
            </div>
            <div class="flex-1 min-w-0">
              <h3 id="dialog-title-session" class="text-base font-semibold text-gray-900">
                {{
                  confirmDialog.type === "single"
                    ? t("deleteSessionConfirmTitle", language)
                    : t("clearAllSessionsConfirmTitle", language)
                }}
              </h3>
              <p class="mt-1.5 text-sm text-gray-600 leading-relaxed break-words">
                <template v-if="confirmDialog.type === 'single'">
                  {{ t("deleteSessionConfirm", language) }}
                  <span
                    v-if="confirmDialog.title"
                    class="block mt-1 font-medium text-gray-800 italic"
                  >
                    „{{ confirmDialog.title }}"
                  </span>
                </template>
                <template v-else>
                  {{ t("clearAllSessionsConfirm", language) }}
                </template>
              </p>
            </div>
          </div>

          <div class="mt-6 flex justify-end gap-2.5">
            <button
              ref="cancelBtnRef"
              type="button"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-400"
              @click="confirmDialog.open = false"
            >
              {{ t("cancel", language) }}
            </button>
            <button
              type="button"
              class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
              @click="handleConfirmDelete"
            >
              {{ t("delete", language) }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

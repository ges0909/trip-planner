import { computed, ref } from "vue";
import {
  deleteFromTrash,
  deleteTour,
  fetchTours,
  fetchTrash,
  renameTour,
  restoreFromTrash,
  type Tour,
  type TrashItem,
} from "../api";

export function useTourLibrary() {
  const tours = ref<Tour[]>([]);
  const trashItems = ref<TrashItem[]>([]);
  const isLoading = ref(false);
  const error = ref("");
  const filterType = ref<"all" | "bike" | "road" | "trash">("all");

  const filteredTours = computed(() => {
    if (filterType.value === "all") return tours.value;
    if (filterType.value === "trash") return [];
    return tours.value.filter((t) => t.tour_type === filterType.value);
  });

  const bikeTours = computed(() => tours.value.filter((t) => t.tour_type === "bike"));
  const roadTours = computed(() => tours.value.filter((t) => t.tour_type === "road"));

  async function loadTours(autoSelectLatest = false): Promise<Tour | null> {
    isLoading.value = true;
    error.value = "";
    try {
      tours.value = await fetchTours();
      if (autoSelectLatest && tours.value.length > 0) {
        const sorted = [...tours.value].sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
        );
        return sorted[0];
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load tours";
    } finally {
      isLoading.value = false;
    }
    return null;
  }

  async function loadTrash() {
    isLoading.value = true;
    error.value = "";
    try {
      trashItems.value = await fetchTrash();
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load trash";
    } finally {
      isLoading.value = false;
    }
  }

  async function removeTour(tourType: string, slug: string): Promise<boolean> {
    try {
      await deleteTour(tourType, slug);
      await loadTours(false);
      return true;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete";
      return false;
    }
  }

  async function renameTourItem(
    tourType: string,
    slug: string,
    newTitle: string,
  ): Promise<Tour | null> {
    try {
      const updated = await renameTour(tourType, slug, newTitle);
      await loadTours(false);
      return updated;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to rename tour";
      return null;
    }
  }

  async function restoreItem(tourType: string, trashName: string): Promise<Tour | null> {
    try {
      const restored = await restoreFromTrash(tourType, trashName);
      await loadTours(false);
      await loadTrash();
      filterType.value = "all";
      return restored as Tour;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to restore";
      return null;
    }
  }

  async function deleteTrashPermanently(tourType: string, trashName: string): Promise<boolean> {
    try {
      await deleteFromTrash(tourType, trashName);
      await loadTrash();
      return true;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete";
      return false;
    }
  }

  return {
    tours,
    trashItems,
    isLoading,
    error,
    filterType,
    filteredTours,
    bikeTours,
    roadTours,
    loadTours,
    loadTrash,
    removeTour,
    renameTourItem,
    restoreItem,
    deleteTrashPermanently,
  };
}

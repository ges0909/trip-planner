import { ref } from "vue";

export function useTourSession() {
  const activityFeedExpanded = ref(true);
  const selectedTourId = ref<string | null>(null);
  const libraryRefreshKey = ref(0);
  const isCommandPaletteOpen = ref(false);
  const isMobileSidebarOpen = ref(false);

  function setSelectedTourId(id: string | null) {
    selectedTourId.value = id;
  }

  function refreshLibrary() {
    libraryRefreshKey.value += 1;
  }

  function openSidebar() {
    isMobileSidebarOpen.value = true;
  }

  function closeSidebar() {
    isMobileSidebarOpen.value = false;
  }

  function toggleSidebar() {
    isMobileSidebarOpen.value = !isMobileSidebarOpen.value;
  }

  function toggleActivityFeed() {
    activityFeedExpanded.value = !activityFeedExpanded.value;
  }

  function setActivityFeedExpanded(value: boolean) {
    activityFeedExpanded.value = value;
  }

  function openCommandPalette() {
    isCommandPaletteOpen.value = true;
  }

  function closeCommandPalette() {
    isCommandPaletteOpen.value = false;
  }

  return {
    activityFeedExpanded,
    selectedTourId,
    libraryRefreshKey,
    isCommandPaletteOpen,
    isMobileSidebarOpen,
    setSelectedTourId,
    refreshLibrary,
    openSidebar,
    closeSidebar,
    toggleSidebar,
    toggleActivityFeed,
    setActivityFeedExpanded,
    openCommandPalette,
    closeCommandPalette,
  };
}

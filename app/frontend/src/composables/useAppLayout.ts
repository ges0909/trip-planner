import { ref } from "vue";

export function useAppLayout() {
  const isMapVisible = ref(true);
  const splitRatio = ref(50);
  const splitContainerRef = ref<HTMLElement | null>(null);

  function startDragging(e: MouseEvent | TouchEvent) {
    window.addEventListener("mousemove", onDragging);
    window.addEventListener("mouseup", stopDragging);
    window.addEventListener("touchmove", onDragging);
    window.addEventListener("touchend", stopDragging);

    if (e instanceof TouchEvent) {
      e.preventDefault();
    }
  }

  function onDragging(e: MouseEvent | TouchEvent) {
    if (!splitContainerRef.value) return;

    const rect = splitContainerRef.value.getBoundingClientRect();
    const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
    const offsetX = clientX - rect.left;
    const percentage = (offsetX / rect.width) * 100;

    splitRatio.value = Math.min(80, Math.max(20, percentage));
  }

  function stopDragging() {
    window.removeEventListener("mousemove", onDragging);
    window.removeEventListener("mouseup", stopDragging);
    window.removeEventListener("touchmove", onDragging);
    window.removeEventListener("touchend", stopDragging);
  }

  function resetSplitRatio() {
    splitRatio.value = 50;
    localStorage.setItem("tourpilot_split_ratio", "50");
  }

  return {
    isMapVisible,
    splitRatio,
    splitContainerRef,
    startDragging,
    resetSplitRatio,
  };
}

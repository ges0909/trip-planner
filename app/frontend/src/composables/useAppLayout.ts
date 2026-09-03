import { ref, watch } from "vue";

function getStoredMapVisible(): boolean {
  try {
    const val = localStorage.getItem("tourpilot_map_visible");
    return val !== null ? val === "true" : true;
  } catch {
    return true;
  }
}

function getStoredSplitRatio(): number {
  try {
    const val = localStorage.getItem("tourpilot_split_ratio");
    if (val) {
      const num = Number(val);
      if (!isNaN(num) && num >= 20 && num <= 80) return num;
    }
  } catch {
    // ignore
  }
  return 50;
}

export function useAppLayout() {
  const isMapVisible = ref(getStoredMapVisible());
  const splitRatio = ref(getStoredSplitRatio());
  const splitContainerRef = ref<HTMLElement | null>(null);

  watch(isMapVisible, (val) => {
    try {
      localStorage.setItem("tourpilot_map_visible", String(val));
    } catch {
      // ignore
    }
  });

  watch(splitRatio, (val) => {
    try {
      localStorage.setItem("tourpilot_split_ratio", String(val));
    } catch {
      // ignore
    }
  });

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
  }

  return {
    isMapVisible,
    splitRatio,
    splitContainerRef,
    startDragging,
    resetSplitRatio,
  };
}

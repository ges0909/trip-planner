import { beforeEach, describe, expect, it } from "vitest";
import { useSession } from "../src/composables/useSession";

describe("useSession composable", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("generates a new uuid session_id when none is stored", () => {
    const { getOrCreateSessionId } = useSession();
    const id = getOrCreateSessionId();

    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    expect(localStorage.getItem("session_id")).toBe(id);
  });

  it("reuses existing session_id from localStorage", () => {
    localStorage.setItem("session_id", "existing-test-session-123");
    const { getOrCreateSessionId } = useSession();

    expect(getOrCreateSessionId()).toBe("existing-test-session-123");
  });
});

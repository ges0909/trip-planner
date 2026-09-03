import { describe, expect, it } from "vitest";
import { sanitizeTourMarkdown } from "../src/utils/markdown";

describe("sanitizeTourMarkdown", () => {
  it("strips frontmatter from markdown", () => {
    const raw = "---\ntitle: Test Tour\ntype: bike\n---\n# My Tour\nDescription";
    const result = sanitizeTourMarkdown(raw);
    expect(result).not.toContain("type: bike");
    expect(result).toContain("My Tour");
    expect(result).toContain("Description");
  });

  it("converts geo coordinates to clickable POI links", () => {
    const raw = "Check out [Eiffel Tower](geo:48.8584,2.2945)";
    const result = sanitizeTourMarkdown(raw);
    expect(result).toContain('data-poi-coords="48.8584,2.2945"');
    expect(result).toContain('data-poi-name="Eiffel Tower"');
    expect(result).toContain("📍 Eiffel Tower");
  });

  it("converts google maps coordinate links to clickable POI links", () => {
    const raw = "Visit [Big Ben](https://maps.google.com/?q=51.5007,-0.1246)";
    const result = sanitizeTourMarkdown(raw);
    expect(result).toContain('data-poi-coords="51.5007,-0.1246"');
    expect(result).toContain('data-poi-name="Big Ben"');
  });

  it("strips raw script tags and XSS injection vectors", () => {
    const raw = "Hello <script>alert(1)</script> <img src='x' onerror='alert(2)'>";
    const result = sanitizeTourMarkdown(raw);
    expect(result).not.toContain("<script>");
    expect(result).not.toContain("onerror");
  });
});

/// <reference types="vite/client" />
import { describe, expect, it } from "vitest";

// Every page source file, as raw text.
const pages = import.meta.glob("/src/pages/*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

describe("no stale placeholder pages", () => {
  it("found the page sources", () => {
    expect(Object.keys(pages).length).toBeGreaterThan(10);
  });

  it.each(Object.entries(pages).filter(([p]) => !p.endsWith(".test.tsx")))(
    "%s does not claim to be 'not built yet'",
    (_path, source) => {
      expect(source).not.toMatch(/isn['’]t built yet|lands in Phase|coming soon/i);
    }
  );
});

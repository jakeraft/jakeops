import { describe, it, expect } from "vitest";
import { formatDateTime } from "./format";

describe("formatDateTime", () => {
  it("converts an ISO 8601 string to YYYY-MM-DD HH:mm format", () => {
    expect(formatDateTime("2026-02-18T15:30:00+09:00")).toBe("2026-02-18 15:30");
  });

  it("returns unparseable values as-is", () => {
    expect(formatDateTime("invalid")).toBe("invalid");
  });

  it("returns an empty string as-is", () => {
    expect(formatDateTime("")).toBe("");
  });
});

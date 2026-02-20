import { describe, it, expect } from "vitest";
import { blockToText, messageToText } from "./transcript";

describe("blockToText", () => {
  it("converts a text block to plain text", () => {
    expect(blockToText({ type: "text", text: "hello" })).toBe("hello");
  });

  it("returns empty string for a text block without text", () => {
    expect(blockToText({ type: "text" })).toBe("");
  });

  it("converts a thinking block with a [thinking] header", () => {
    const result = blockToText({ type: "thinking", thinking: "hmm" });
    expect(result).toBe("[thinking]\nhmm");
  });

  it("converts a tool_use block with a [tool_use: name] header", () => {
    const result = blockToText({ type: "tool_use", name: "Read", input: { path: "/a" } });
    expect(result).toContain("[tool_use: Read]");
    expect(result).toContain('"/a"');
  });

  it("converts string content in a tool_result block", () => {
    const result = blockToText({ type: "tool_result", content: "ok" });
    expect(result).toBe("[tool_result]\nok");
  });

  it("converts object content in a tool_result block to JSON", () => {
    const result = blockToText({ type: "tool_result", content: { status: "done" } });
    expect(result).toContain("[tool_result]");
    expect(result).toContain('"status"');
  });

  it("converts unknown types to JSON", () => {
    const result = blockToText({ type: "unknown_type" });
    expect(result).toContain('"unknown_type"');
  });
});

describe("messageToText", () => {
  it("converts a string content message", () => {
    const result = messageToText({
      timestamp: "2026-02-18T10:00:00Z",
      type: "message",
      role: "user",
      content: "hello",
    });
    expect(result).toContain("--- user");
    expect(result).toContain("hello");
  });

  it("converts an array content message", () => {
    const result = messageToText({
      timestamp: "2026-02-18T10:00:00Z",
      type: "message",
      role: "assistant",
      content: [{ type: "text", text: "world" }],
    });
    expect(result).toContain("--- assistant");
    expect(result).toContain("world");
  });

  it("returns only the header for a null content message", () => {
    const result = messageToText({
      timestamp: "",
      type: "message",
      role: "user",
      content: null,
    });
    expect(result).toBe("--- user  ---");
  });
});

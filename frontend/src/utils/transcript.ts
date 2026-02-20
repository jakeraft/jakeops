interface ContentBlock {
  type: string;
  text?: string;
  thinking?: string;
  name?: string;
  input?: unknown;
  content?: unknown;
  tool_use_id?: string;
}

interface TranscriptMessage {
  timestamp: string;
  type: string;
  role: string;
  content: ContentBlock[] | string | null;
}

export type { ContentBlock, TranscriptMessage };

export const blockToText = (block: ContentBlock): string => {
  if (block.type === "text") return block.text ?? "";
  if (block.type === "thinking") return `[thinking]\n${block.thinking ?? ""}`;
  if (block.type === "tool_use") return `[tool_use: ${block.name}]\n${JSON.stringify(block.input, null, 2)}`;
  if (block.type === "tool_result") {
    const text = typeof block.content === "string" ? block.content : JSON.stringify(block.content, null, 2);
    return `[tool_result]\n${text}`;
  }
  return JSON.stringify(block, null, 2);
};

export const messageToText = (msg: TranscriptMessage): string => {
  const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : "";
  const header = `--- ${msg.role} ${time} ---`;
  if (typeof msg.content === "string") return `${header}\n${msg.content}`;
  if (Array.isArray(msg.content)) return `${header}\n${msg.content.map(blockToText).join("\n")}`;
  return header;
};

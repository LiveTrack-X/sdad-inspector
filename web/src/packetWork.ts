export interface PacketWorkItem {
  text: string;
  completed: boolean;
  packetId: string;
  section: string;
}

export function packetWorkItems(markdown: string | null | undefined, packetId: string | null | undefined): PacketWorkItem[] {
  if (!markdown || !packetId) return [];
  const result: PacketWorkItem[] = [];
  const lines = markdown.split(/\r?\n/);
  let current: PacketWorkItem | null = null;
  let section = "Document";
  for (const line of lines) {
    const heading = line.match(/^#{2,6}\s+(.+?)\s*$/);
    if (heading) {
      section = heading[1].trim();
      current = null;
      continue;
    }
    const match = line.match(/^- \[([ xX])\] \[packet:([^\]]+)\]\s*(.*)$/);
    if (match) {
      current = {
        completed: match[1].toLocaleLowerCase() === "x",
        packetId: match[2],
        text: match[3].trim(),
        section,
      };
      if (current.packetId === packetId) result.push(current);
      continue;
    }
    if (current?.packetId === packetId && /^\s{2,}\S/.test(line) && result.length) {
      result[result.length - 1].text += ` ${line.trim()}`;
    } else if (line.startsWith("## ") || /^- \[[ xX]\]/.test(line)) {
      current = null;
    }
    if (result.length >= 40) break;
  }
  return result;
}

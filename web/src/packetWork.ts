export type PacketControlPhase = "plan" | "route" | "implement" | "verify" | "report";

export interface PacketWorkItem {
  text: string;
  completed: boolean;
  packetId: string;
  section: string;
  current: boolean;
  phase: PacketControlPhase | null;
  phaseConflict: boolean;
}

const CONTROL_PHASES = new Set<PacketControlPhase>(["plan", "route", "implement", "verify", "report"]);

function presentationMetadata(value: string): {
  text: string;
  current: boolean;
  phase: PacketControlPhase | null;
  phaseConflict: boolean;
} {
  let text = value.trim();
  let current = false;
  let phase: PacketControlPhase | null = null;
  let phaseConflict = false;
  while (true) {
    const token = text.match(/^\[([^\]]+)\]\s*/);
    if (!token) break;
    const normalized = token[1].trim().toLocaleLowerCase();
    if (normalized === "current") {
      current = true;
    } else if (normalized.startsWith("phase:")) {
      const candidate = normalized.slice("phase:".length).trim() as PacketControlPhase;
      if (!CONTROL_PHASES.has(candidate) || (phase !== null && phase !== candidate)) {
        phaseConflict = true;
      } else {
        phase = candidate;
      }
    } else {
      break;
    }
    text = text.slice(token[0].length).trimStart();
  }
  return { text, current, phase, phaseConflict };
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
      const metadata = presentationMetadata(match[3]);
      current = {
        completed: match[1].toLocaleLowerCase() === "x",
        packetId: match[2],
        text: metadata.text,
        section,
        current: metadata.current,
        phase: metadata.phase,
        phaseConflict: metadata.phaseConflict,
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

import type { LiveDocument, LiveDocuments, Snapshot } from "./types";

export type PacketControlPhase = "plan" | "route" | "implement" | "verify" | "report";

export interface PacketWorkItem {
  text: string;
  completed: boolean;
  packetId: string;
  section: string;
  sectionPath?: string[];
  current: boolean;
  phase: PacketControlPhase | null;
  phaseConflict: boolean;
  summary?: string;
  detail?: string;
  line?: number;
}

const CONTROL_PHASES = new Set<PacketControlPhase>(["plan", "route", "implement", "verify", "report"]);

export function packetWorkSource(snapshot: Snapshot | null, documents: LiveDocuments | null): {document: LiveDocument | null; complete: boolean} {
  const document = snapshot && documents?.project_root === snapshot.project.root
    ? documents.documents.find(item => item.path === snapshot.protocol.todo_path) ?? null : null;
  const complete = Boolean(snapshot?.state.available && snapshot.state.active_packet && snapshot.inspection_status === "completed"
    && document?.exists && typeof document.content === "string" && !document.error && !document.truncated);
  return {document,complete};
}

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
  const headings: Array<{level:number;text:string}> = [];
  let fence: {marker:string;length:number;task:PacketWorkItem|null} | null = null;
  function appendDetail(item:PacketWorkItem|null,line:string) {
    if (!item || item.packetId !== packetId) return;
    item.text += ` ${line.trim()}`;
    item.detail += `\n${line.startsWith("  ") ? line.slice(2) : line}`;
  }
  for (const [index, line] of lines.entries()) {
    const marker = line.match(/^( {0,3})(`{3,}|~{3,})(.*)$/);
    if (fence) {
      appendDetail(fence.task,line);
      if (marker && marker[2][0] === fence.marker && marker[2].length >= fence.length && /^[ \t]*$/.test(marker[3])) {
        current = fence.task;
        fence = null;
      }
      continue;
    }
    if (marker && (marker[2][0] === "~" || !marker[3].includes("`"))) {
      const task: PacketWorkItem | null = marker[1].length >= 2 ? current : null;
      appendDetail(task,line);
      fence = {marker:marker[2][0],length:marker[2].length,task};
      current = null;
      continue;
    }
    const heading = line.match(/^ {0,3}(#{1,6})(?:[ \t]+(.*)|[ \t]*)$/);
    if (heading) {
      const level = heading[1].length;
      section = (heading[2] ?? "").replace(/[ \t]+#+[ \t]*$/, "").trim();
      while (headings.length && headings[headings.length-1].level >= level) headings.pop();
      headings.push({level,text:section});
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
        sectionPath: headings.map(heading => heading.text),
        current: metadata.current,
        phase: metadata.phase,
        phaseConflict: metadata.phaseConflict,
        summary: metadata.text,
        detail: metadata.text,
        line: index + 1,
      };
      if (current.packetId === packetId) result.push(current);
      continue;
    }
    if (current?.packetId === packetId && /^\s{2,}\S/.test(line) && result.length) {
      appendDetail(current,line);
    } else if (line.startsWith("## ") || /^- \[[ xX]\]/.test(line)) {
      current = null;
    }
  }
  return result;
}

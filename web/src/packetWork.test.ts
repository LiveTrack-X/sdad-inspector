import { describe, expect, it } from "vitest";
import { packetWorkItems } from "./packetWork";

describe("packetWorkItems", () => {
  it("parses explicit current-phase metadata without displaying marker syntax", () => {
    const work = packetWorkItems(
      "## Active Work\n\n- [ ] [packet:demo] [phase:Implement] [current] Build the exact view.\n  Keep the continuation.",
      "demo",
    );

    expect(work).toEqual([{
      completed: false,
      current: true,
      packetId: "demo",
      phase: "implement",
      phaseConflict: false,
      section: "Active Work",
      text: "Build the exact view. Keep the continuation.",
    }]);
  });

  it("keeps ordinary bracketed task copy and rejects invalid or conflicting phases", () => {
    const work = packetWorkItems(
      [
        "## Active Work",
        "",
        "- [ ] [packet:demo] [frontend] Preserve this label.",
        "- [ ] [packet:demo] [current] [phase:Plan] [phase:Verify] Ambiguous stage.",
        "- [ ] [packet:demo] [current] [phase:Build] Unsupported stage.",
      ].join("\n"),
      "demo",
    );

    expect(work[0]).toMatchObject({ text: "[frontend] Preserve this label.", current: false, phase: null, phaseConflict: false });
    expect(work[1]).toMatchObject({ text: "Ambiguous stage.", current: true, phase: "plan", phaseConflict: true });
    expect(work[2]).toMatchObject({ text: "Unsupported stage.", current: true, phase: null, phaseConflict: true });
  });
});

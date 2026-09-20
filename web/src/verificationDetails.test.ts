import { describe, expect, it } from "vitest";
import { verificationCopy } from "./verificationCopy";
import { explainVerificationReason } from "./verificationDetails";

describe("receipt evidence explanations", () => {
  it.each(["en", "ko", "ja", "zh-CN"] as const)("maps only recognized codes in %s", locale => {
    const c = verificationCopy[locale];
    expect(explainVerificationReason("receipt_source_incomplete", c)).toBe(c.reasonIncompleteSource);
    expect(explainVerificationReason("changed_during_run", c)).toBe(c.reasonChangedDuring);
    expect(explainVerificationReason("declared_bytes_match", c)).toBe(c.reasonMatched);
    expect(explainVerificationReason("changed_since_run", c)).toBe(c.reasonChangedSince);
    expect(explainVerificationReason("source_unreadable_unsafe_or_over_budget", c)).toBe(c.reasonUnreadable);
    expect(explainVerificationReason("owner explanation", c)).toBe(c.reasonOther);
    expect(explainVerificationReason("__proto__", c)).toBe(c.reasonOther);
  });
});

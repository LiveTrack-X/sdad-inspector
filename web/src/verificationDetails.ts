import type { verificationCopy } from "./verificationCopy";

const reasonKeys = {
  receipt_source_incomplete: "reasonIncompleteSource",
  changed_during_run: "reasonChangedDuring",
  declared_bytes_match: "reasonMatched",
  changed_since_run: "reasonChangedSince",
  source_unreadable_unsafe_or_over_budget: "reasonUnreadable",
} as const;

export function explainVerificationReason(reason: string, copy: (typeof verificationCopy)["en"]): string {
  const key = Object.prototype.hasOwnProperty.call(reasonKeys, reason) ? reasonKeys[reason as keyof typeof reasonKeys] : null;
  return key ? copy[key] : copy.reasonOther;
}

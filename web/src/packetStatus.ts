import type { Translate } from "./i18n";

// Interpret the existing declaration; never infer verification or acceptance.
export function packetStatusMeaning(status: string | undefined, t: Translate): string {
  if (status === "software_verified") return t("packetSoftwareVerifiedMeaning");
  if (status === "ai_complete") return t("packetAiCompleteMeaning");
  if (status === "deferred") return t("packetDeferredMeaning");
  if (status === "owner_accepted") return t("packetAcceptedMeaning");
  return t("packetStatusMeaning");
}

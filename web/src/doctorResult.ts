import type { Snapshot } from "./types";

/** Structural Doctor evidence only; this never establishes execution of declared validation. */
export function doctorResult(snapshot: Snapshot): { available: boolean; passed: boolean } {
  const doctor = snapshot.doctor;
  const available = snapshot.inspection_status === "completed"
    && doctor.completed
    && doctor.diagnostic_error === null
    && (doctor.exit_code === 0 || doctor.exit_code === 1)
    && snapshot.integrity.control_files_unchanged_during_inspection;
  return {
    available,
    passed: available && doctor.exit_code === 0
      && doctor.summary.errors === 0 && doctor.summary.warnings === 0
      && !doctor.findings.some((finding) => finding.severity === "error" || finding.severity === "warning"),
  };
}

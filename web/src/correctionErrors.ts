import {ApiError} from './api';
import type {InteractionCopy} from './interactionCopy';
export function correctionError(error: unknown, copy: InteractionCopy): string {
  if (!(error instanceof ApiError)) return copy.error;
  const keys = {correction_capacity: 'capacity', correction_storage: 'storageError', correction_conflict: 'conflictError', correction_archived: 'archivedError', correction_invalid: 'invalidError', correction_project: 'projectError', request_too_large: 'invalidError'} as const;
  return copy[keys[error.code as keyof typeof keys]] ?? copy.error;
}

export const VAULT_SIDECAR_PROTOCOL = "ai-session-vault-sidecar" as const;
export const VAULT_SIDECAR_PROTOCOL_VERSION = 1 as const;
export const VAULT_SIDECAR_EVENT_NAME = "vault-sidecar-event" as const;

export type VaultSidecarOperation =
  | "list-apps"
  | "inspect"
  | "layout"
  | "sync"
  | "verify"
  | "restore";

export type VaultRestoreScope = "session" | "full";
export type VaultSidecarEventType =
  | "started"
  | "progress"
  | "completed"
  | "failed";

export interface VaultSidecarRequest {
  operation: VaultSidecarOperation;
  appId?: string;
  vaultRoot?: string;
  sourceRoot?: string;
  machineId?: string;
  restoreRoot?: string;
  restoreScope?: VaultRestoreScope;
  sessionId?: string;
  dryRun?: boolean;
  requestId?: string;
  timeoutSeconds?: number;
}

export interface VaultSidecarStatus {
  available: boolean;
  protocol: typeof VAULT_SIDECAR_PROTOCOL;
  protocolVersion: typeof VAULT_SIDECAR_PROTOCOL_VERSION;
  entrypoint: string;
  program: string;
  launchMode: "python-script" | "executable";
  reason?: string | null;
}

export interface VaultSidecarCommandPreview {
  program: string;
  args: string[];
  requestId: string;
  operation: VaultSidecarOperation;
  protocol: typeof VAULT_SIDECAR_PROTOCOL;
  protocolVersion: typeof VAULT_SIDECAR_PROTOCOL_VERSION;
  timeoutSeconds: number;
}

export interface VaultSidecarTaskStart {
  requestId: string;
  operation: VaultSidecarOperation;
  timeoutSeconds: number;
  startedAt: string;
}

export interface VaultSidecarTaskInfo {
  requestId: string;
  operation: VaultSidecarOperation;
  startedAt: string;
  timeoutSeconds: number;
  cancelRequested: boolean;
  status: "running" | "cancelling";
}

export interface VaultSidecarError {
  code: string;
  message: string;
  retryable: boolean;
  details?: unknown;
}

export interface VaultSidecarProgress {
  stage: string;
  message: string;
  current?: number;
  total?: number;
  details?: Record<string, unknown>;
}

export interface VaultSidecarEvent<TData = unknown> {
  protocol: typeof VAULT_SIDECAR_PROTOCOL;
  protocol_version: typeof VAULT_SIDECAR_PROTOCOL_VERSION;
  request_id: string;
  sequence: number;
  timestamp: string;
  operation: VaultSidecarOperation;
  event: VaultSidecarEventType;
  data?: TData;
  error?: VaultSidecarError;
}

export interface VaultAdapterInfo {
  app_id: string;
  display_name: string;
  aliases: string[];
  default_source_root: string;
  restore_strategy?: string | null;
}

export interface VaultListAppsResult {
  adapters: VaultAdapterInfo[];
}

export interface VaultConsoleConfig {
  vaultRoot: string;
  machineId: string;
  sourceRoot: string;
  restoreRoot: string;
  restoreScope: VaultRestoreScope;
  sessionId: string;
  selectedAppId: string;
}

export interface VaultTaskRecord {
  requestId: string;
  operation: VaultSidecarOperation;
  startedAt: string;
  status: "running" | "completed" | "failed" | "cancelled";
  events: VaultSidecarEvent[];
  result?: unknown;
  error?: VaultSidecarError;
}

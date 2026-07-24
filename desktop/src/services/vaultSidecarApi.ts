import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import type {
  VaultSidecarCommandPreview,
  VaultSidecarEvent,
  VaultSidecarRequest,
  VaultSidecarStatus,
  VaultSidecarTaskInfo,
  VaultSidecarTaskStart,
} from "@/types/vaultSidecar";
import { VAULT_SIDECAR_EVENT_NAME } from "@/types/vaultSidecar";

export async function getVaultSidecarStatus(): Promise<VaultSidecarStatus> {
  return invoke<VaultSidecarStatus>("get_vault_sidecar_status");
}

export async function previewVaultSidecarCommand(
  request: VaultSidecarRequest,
): Promise<VaultSidecarCommandPreview> {
  return invoke<VaultSidecarCommandPreview>("preview_vault_sidecar_command", {
    request,
  });
}

export async function startVaultSidecarTask(
  request: VaultSidecarRequest,
): Promise<VaultSidecarTaskStart> {
  return invoke<VaultSidecarTaskStart>("start_vault_sidecar_task", { request });
}

export async function cancelVaultSidecarTask(
  requestId: string,
): Promise<boolean> {
  return invoke<boolean>("cancel_vault_sidecar_task", { requestId });
}

export async function listVaultSidecarTasks(): Promise<VaultSidecarTaskInfo[]> {
  return invoke<VaultSidecarTaskInfo[]>("list_vault_sidecar_tasks");
}

export async function listenVaultSidecarEvents(
  handler: (event: VaultSidecarEvent) => void,
): Promise<UnlistenFn> {
  return listen<VaultSidecarEvent>(VAULT_SIDECAR_EVENT_NAME, ({ payload }) => {
    handler(payload);
  });
}

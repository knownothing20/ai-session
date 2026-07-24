import { invoke } from '@tauri-apps/api/core';

import type {
  VaultSidecarCommandPreview,
  VaultSidecarRequest,
  VaultSidecarStatus,
} from '@/types/vaultSidecar';

/**
 * These commands are implemented in Rust during phase 1 task package 1.
 * They become callable after registration in the Tauri invoke handler.
 */
export async function getVaultSidecarStatus(): Promise<VaultSidecarStatus> {
  return invoke<VaultSidecarStatus>('get_vault_sidecar_status');
}

export async function previewVaultSidecarCommand(
  request: VaultSidecarRequest,
): Promise<VaultSidecarCommandPreview> {
  return invoke<VaultSidecarCommandPreview>('preview_vault_sidecar_command', {
    request,
  });
}

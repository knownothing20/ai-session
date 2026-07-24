import { invoke } from '@tauri-apps/api/core';

import type {
  VaultSidecarCommandPreview,
  VaultSidecarRequest,
  VaultSidecarStatus,
} from '@/types/vaultSidecar';

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

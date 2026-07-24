import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";
import type { VaultSidecarEvent } from "@/types/vaultSidecar";

const getStatus = vi.fn();
const listTasks = vi.fn();
const startTask = vi.fn();
const previewCommand = vi.fn();
const cancelTask = vi.fn();
let eventHandler: ((event: VaultSidecarEvent) => void) | null = null;

vi.mock("@/services/vaultSidecarApi", () => ({
  getVaultSidecarStatus: (...args: unknown[]) => getStatus(...args),
  listVaultSidecarTasks: (...args: unknown[]) => listTasks(...args),
  startVaultSidecarTask: (...args: unknown[]) => startTask(...args),
  previewVaultSidecarCommand: (...args: unknown[]) => previewCommand(...args),
  cancelVaultSidecarTask: (...args: unknown[]) => cancelTask(...args),
  listenVaultSidecarEvents: vi.fn(
    async (handler: (event: VaultSidecarEvent) => void) => {
      eventHandler = handler;
      return vi.fn();
    },
  ),
}));

import { VaultConsoleModal } from "@/components/modals/vault/VaultConsoleModal";

beforeEach(() => {
  eventHandler = null;
  getStatus.mockReset();
  listTasks.mockReset();
  startTask.mockReset();
  previewCommand.mockReset();
  cancelTask.mockReset();

  getStatus.mockResolvedValue({
    available: true,
    protocol: "ai-session-vault-sidecar",
    protocolVersion: 1,
    entrypoint: "D:/GitHub/ai-session/scripts/vault_sync.py",
    program: "python",
    launchMode: "python-script",
    reason: null,
  });
  listTasks.mockResolvedValue([]);
  startTask.mockImplementation(async (request) => ({
    requestId: request.requestId,
    operation: request.operation,
    timeoutSeconds: request.timeoutSeconds ?? 120,
    startedAt: "2026-07-24T00:00:00Z",
  }));
  previewCommand.mockImplementation(async (request) => ({
    program: "python",
    args: ["vault_sync.py", "--mode", request.operation],
    requestId: request.requestId,
    operation: request.operation,
    protocol: "ai-session-vault-sidecar",
    protocolVersion: 1,
    timeoutSeconds: request.timeoutSeconds,
  }));
});

describe("VaultConsoleModal", () => {
  it("discovers adapters and starts a backup dry-run", async () => {
    render(<VaultConsoleModal isOpen={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(startTask).toHaveBeenCalledWith(
        expect.objectContaining({ operation: "list-apps" }),
      );
    });
    expect(eventHandler).not.toBeNull();

    const discoveryRequest = startTask.mock.calls[0][0];
    await act(async () => {
      eventHandler?.({
        protocol: "ai-session-vault-sidecar",
        protocol_version: 1,
        request_id: discoveryRequest.requestId,
        sequence: 2,
        timestamp: "2026-07-24T00:00:01Z",
        operation: "list-apps",
        event: "completed",
        data: {
          adapters: [
            {
              app_id: "codex",
              display_name: "OpenAI Codex",
              aliases: ["codex"],
              default_source_root: "C:/Users/test/.codex",
              restore_strategy: "codex-rollout-backfill",
            },
          ],
        },
      });
    });

    expect(await screen.findByText("OpenAI Codex")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("D:\\AI-Session-Vault"), {
      target: { value: "D:/Vault" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Backup dry-run" }));

    await waitFor(() => {
      expect(previewCommand).toHaveBeenCalledWith(
        expect.objectContaining({
          operation: "sync",
          appId: "codex",
          vaultRoot: "D:/Vault",
          dryRun: true,
        }),
      );
    });
    expect(startTask).toHaveBeenLastCalledWith(
      expect.objectContaining({ operation: "sync", dryRun: true }),
    );
  });
});

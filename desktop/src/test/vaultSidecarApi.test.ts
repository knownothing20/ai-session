import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  invoke: vi.fn(),
  listen: vi.fn(),
}));

vi.mock("@tauri-apps/api/core", () => ({ invoke: mocks.invoke }));
vi.mock("@tauri-apps/api/event", () => ({ listen: mocks.listen }));

import {
  cancelVaultSidecarTask,
  getVaultSidecarStatus,
  listenVaultSidecarEvents,
  listVaultSidecarTasks,
  previewVaultSidecarCommand,
  startVaultSidecarTask,
} from "@/services/vaultSidecarApi";

beforeEach(() => {
  mocks.invoke.mockReset();
  mocks.listen.mockReset();
});

describe("Vault Sidecar API", () => {
  it("uses the registered Tauri command names", async () => {
    mocks.invoke.mockResolvedValue(undefined);
    const request = {
      operation: "sync" as const,
      appId: "codex",
      vaultRoot: "D:/Vault",
      dryRun: true,
      requestId: "request-1",
    };

    await getVaultSidecarStatus();
    await previewVaultSidecarCommand(request);
    await startVaultSidecarTask(request);
    await cancelVaultSidecarTask("request-1");
    await listVaultSidecarTasks();

    expect(mocks.invoke).toHaveBeenNthCalledWith(1, "get_vault_sidecar_status");
    expect(mocks.invoke).toHaveBeenNthCalledWith(
      2,
      "preview_vault_sidecar_command",
      { request },
    );
    expect(mocks.invoke).toHaveBeenNthCalledWith(3, "start_vault_sidecar_task", {
      request,
    });
    expect(mocks.invoke).toHaveBeenNthCalledWith(4, "cancel_vault_sidecar_task", {
      requestId: "request-1",
    });
    expect(mocks.invoke).toHaveBeenNthCalledWith(5, "list_vault_sidecar_tasks");
  });

  it("subscribes to the versioned Vault event channel", async () => {
    const unlisten = vi.fn();
    const handler = vi.fn();
    mocks.listen.mockResolvedValue(unlisten);

    const returned = await listenVaultSidecarEvents(handler);
    const callback = mocks.listen.mock.calls[0][1];
    callback({
      payload: {
        protocol: "ai-session-vault-sidecar",
        protocol_version: 1,
        request_id: "request-1",
        sequence: 1,
        timestamp: "2026-07-24T00:00:00Z",
        operation: "inspect",
        event: "started",
      },
    });

    expect(mocks.listen).toHaveBeenCalledWith(
      "vault-sidecar-event",
      expect.any(Function),
    );
    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({ request_id: "request-1", event: "started" }),
    );
    expect(returned).toBe(unlisten);
  });
});

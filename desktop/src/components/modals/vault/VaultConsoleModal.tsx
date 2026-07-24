import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  AlertTriangle,
  CheckCircle2,
  DatabaseBackup,
  FolderSearch,
  Loader2,
  Play,
  RotateCcw,
  ShieldCheck,
  Square,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
} from "@/components/ui";
import {
  cancelVaultSidecarTask,
  getVaultSidecarStatus,
  listenVaultSidecarEvents,
  listVaultSidecarTasks,
  previewVaultSidecarCommand,
  startVaultSidecarTask,
} from "@/services/vaultSidecarApi";
import type {
  VaultAdapterInfo,
  VaultConsoleConfig,
  VaultListAppsResult,
  VaultSidecarCommandPreview,
  VaultSidecarError,
  VaultSidecarEvent,
  VaultSidecarOperation,
  VaultSidecarProgress,
  VaultSidecarRequest,
  VaultSidecarStatus,
  VaultTaskRecord,
} from "@/types/vaultSidecar";

const CONFIG_STORAGE_KEY = "ai-session-vault-console-v1";

const DEFAULT_CONFIG: VaultConsoleConfig = {
  vaultRoot: "",
  machineId: "",
  sourceRoot: "",
  restoreRoot: "",
  restoreScope: "session",
  sessionId: "",
  selectedAppId: "codex",
};

interface VaultConsoleModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function loadConfig(): VaultConsoleConfig {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) return DEFAULT_CONFIG;
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) } as VaultConsoleConfig;
  } catch {
    return DEFAULT_CONFIG;
  }
}

function requestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID().replaceAll("-", "");
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asProgress(value: unknown): VaultSidecarProgress | null {
  if (!isRecord(value)) return null;
  if (typeof value.stage !== "string" || typeof value.message !== "string") {
    return null;
  }
  return value as unknown as VaultSidecarProgress;
}

function extractReportPath(value: unknown): string | null {
  if (!isRecord(value)) return null;
  const direct = value.report_path;
  if (typeof direct === "string" && direct.length > 0) return direct;
  const restore = value.restore_root;
  if (typeof restore === "string" && restore.length > 0) return restore;
  const machine = value.machine_root;
  if (typeof machine === "string" && machine.length > 0) return machine;
  return null;
}

function progressPercent(progress: VaultSidecarProgress | null): number | null {
  if (
    progress?.current == null ||
    progress.total == null ||
    progress.total <= 0
  ) {
    return null;
  }
  return Math.max(0, Math.min(100, (progress.current / progress.total) * 100));
}

function applyTaskEvent(
  records: VaultTaskRecord[],
  event: VaultSidecarEvent,
): VaultTaskRecord[] {
  return records.map((record) => {
    if (record.requestId !== event.request_id) return record;
    const terminalStatus =
      event.event === "completed"
        ? "completed"
        : event.event === "failed"
          ? event.error?.code === "cancelled" || event.error?.code === "CANCELLED"
            ? "cancelled"
            : "failed"
          : record.status;
    return {
      ...record,
      status: terminalStatus,
      events: [...record.events, event],
      result: event.event === "completed" ? event.data : record.result,
      error: event.event === "failed" ? event.error : record.error,
    };
  });
}

export function VaultConsoleModal({ isOpen, onClose }: VaultConsoleModalProps) {
  const { t } = useTranslation();
  const [config, setConfig] = useState<VaultConsoleConfig>(loadConfig);
  const [status, setStatus] = useState<VaultSidecarStatus | null>(null);
  const [adapters, setAdapters] = useState<VaultAdapterInfo[]>([]);
  const [activeRequestId, setActiveRequestId] = useState<string | null>(null);
  const [activeOperation, setActiveOperation] =
    useState<VaultSidecarOperation | null>(null);
  const [events, setEvents] = useState<VaultSidecarEvent[]>([]);
  const [progress, setProgress] = useState<VaultSidecarProgress | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<VaultSidecarError | null>(null);
  const [preview, setPreview] = useState<VaultSidecarCommandPreview | null>(null);
  const [tasks, setTasks] = useState<VaultTaskRecord[]>([]);
  const [isInitializing, setIsInitializing] = useState(false);
  const activeRequestRef = useRef<string | null>(null);
  const discoveryRequestRef = useRef<string | null>(null);

  const selectedAdapter = useMemo(
    () => adapters.find((item) => item.app_id === config.selectedAppId) ?? null,
    [adapters, config.selectedAppId],
  );
  const canRestore = selectedAdapter?.restore_strategy != null;
  const percent = progressPercent(progress);
  const reportPath = extractReportPath(result);

  const updateConfig = useCallback(
    (
      key: keyof VaultConsoleConfig,
      value: VaultConsoleConfig[keyof VaultConsoleConfig],
    ) => {
      setConfig((current) => ({ ...current, [key]: value }));
    },
    [],
  );

  useEffect(() => {
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
  }, [config]);

  const recordEvent = useCallback(
    (event: VaultSidecarEvent) => {
      const isDiscovery = event.request_id === discoveryRequestRef.current;
      const isActive = event.request_id === activeRequestRef.current;
      if (!isDiscovery && !isActive) return;

      setTasks((current) => applyTaskEvent(current, event));

      if (isActive) {
        setEvents((current) => [...current, event]);
        if (event.event === "progress") {
          setProgress(asProgress(event.data));
        }
        if (event.event === "completed") {
          setResult(event.data ?? null);
          setError(null);
          setProgress(null);
          setActiveRequestId(null);
          setActiveOperation(null);
          activeRequestRef.current = null;
        }
        if (event.event === "failed") {
          setError(
            event.error ?? {
              code: "unknown_error",
              message: t("vault.errors.unknown"),
              retryable: false,
            },
          );
          setProgress(null);
          setActiveRequestId(null);
          setActiveOperation(null);
          activeRequestRef.current = null;
        }
      }

      if (isDiscovery && event.event === "completed" && isRecord(event.data)) {
        const data = event.data as unknown as VaultListAppsResult;
        if (Array.isArray(data.adapters)) {
          setAdapters(data.adapters);
          setConfig((current) => {
            const selectedExists = data.adapters.some(
              (adapter) => adapter.app_id === current.selectedAppId,
            );
            return selectedExists
              ? current
              : { ...current, selectedAppId: data.adapters[0]?.app_id ?? "" };
          });
        }
        discoveryRequestRef.current = null;
      }
      if (isDiscovery && event.event === "failed") {
        setError(
          event.error ?? {
            code: "discovery_failed",
            message: t("vault.errors.unknown"),
            retryable: true,
          },
        );
        discoveryRequestRef.current = null;
      }
    },
    [t],
  );

  useEffect(() => {
    if (!isOpen) return undefined;
    let disposed = false;
    let unlisten: (() => void) | undefined;

    const initialize = async () => {
      setIsInitializing(true);
      try {
        unlisten = await listenVaultSidecarEvents(recordEvent);
        const nextStatus = await getVaultSidecarStatus();
        if (disposed) return;
        setStatus(nextStatus);
        const running = await listVaultSidecarTasks();
        if (!disposed && running.length > 0) {
          const records = running.map((task) => ({
            requestId: task.requestId,
            operation: task.operation,
            startedAt: task.startedAt,
            status: "running" as const,
            events: [],
          }));
          setTasks(records);
          const first = running[0];
          activeRequestRef.current = first.requestId;
          setActiveRequestId(first.requestId);
          setActiveOperation(first.operation);
        }
        if (nextStatus.available) {
          const discoveryId = requestId();
          discoveryRequestRef.current = discoveryId;
          await startVaultSidecarTask({
            operation: "list-apps",
            requestId: discoveryId,
            timeoutSeconds: 120,
          });
        }
      } catch (nextError) {
        if (!disposed) {
          setError({
            code: "initialization_failed",
            message:
              nextError instanceof Error ? nextError.message : String(nextError),
            retryable: true,
          });
        }
      } finally {
        if (!disposed) setIsInitializing(false);
      }
    };

    void initialize();
    return () => {
      disposed = true;
      unlisten?.();
    };
  }, [isOpen, recordEvent]);

  const buildRequest = useCallback(
    (
      operation: VaultSidecarOperation,
      dryRun = false,
      explicitRequestId = requestId(),
    ): VaultSidecarRequest => ({
      operation,
      appId: operation === "list-apps" ? undefined : config.selectedAppId,
      vaultRoot: config.vaultRoot.trim() || undefined,
      sourceRoot: config.sourceRoot.trim() || undefined,
      machineId: config.machineId.trim() || undefined,
      restoreRoot: config.restoreRoot.trim() || undefined,
      restoreScope: config.restoreScope,
      sessionId: config.sessionId.trim() || undefined,
      dryRun,
      requestId: explicitRequestId,
      timeoutSeconds:
        operation === "sync" || operation === "restore" ? 3600 : 600,
    }),
    [config],
  );

  const validateOperation = useCallback(
    (operation: VaultSidecarOperation): string | null => {
      if (operation !== "list-apps" && !config.selectedAppId) {
        return t("vault.errors.appRequired");
      }
      if (
        ["layout", "sync", "verify", "restore"].includes(operation) &&
        !config.vaultRoot.trim()
      ) {
        return t("vault.errors.vaultRequired");
      }
      if (operation === "restore") {
        if (!canRestore) return t("vault.errors.restoreUnsupported");
        if (!config.restoreRoot.trim()) return t("vault.errors.restoreRootRequired");
        if (config.restoreScope === "session" && !config.sessionId.trim()) {
          return t("vault.errors.sessionRequired");
        }
      }
      return null;
    },
    [canRestore, config, t],
  );

  const runOperation = useCallback(
    async (operation: VaultSidecarOperation, dryRun = false) => {
      if (activeRequestRef.current) return;
      const validation = validateOperation(operation);
      if (validation) {
        setError({ code: "invalid_input", message: validation, retryable: false });
        return;
      }
      if (!dryRun && operation === "sync") {
        if (!window.confirm(t("vault.confirm.sync"))) return;
      }
      if (!dryRun && operation === "restore") {
        if (!window.confirm(t("vault.confirm.restore"))) return;
      }

      const nextRequestId = requestId();
      const request = buildRequest(operation, dryRun, nextRequestId);
      setError(null);
      setResult(null);
      setEvents([]);
      setProgress(null);
      setPreview(null);
      activeRequestRef.current = nextRequestId;
      setActiveRequestId(nextRequestId);
      setActiveOperation(operation);
      setTasks((current) => [
        {
          requestId: nextRequestId,
          operation,
          startedAt: new Date().toISOString(),
          status: "running",
          events: [],
        },
        ...current.slice(0, 9),
      ]);

      try {
        const nextPreview = await previewVaultSidecarCommand(request);
        setPreview(nextPreview);
        await startVaultSidecarTask(request);
      } catch (nextError) {
        const message =
          nextError instanceof Error ? nextError.message : String(nextError);
        const startError: VaultSidecarError = {
          code: "start_failed",
          message,
          retryable: true,
        };
        setError(startError);
        setTasks((current) =>
          current.map((task) =>
            task.requestId === nextRequestId
              ? { ...task, status: "failed", error: startError }
              : task,
          ),
        );
        setActiveRequestId(null);
        setActiveOperation(null);
        activeRequestRef.current = null;
      }
    },
    [buildRequest, t, validateOperation],
  );

  const cancelActive = useCallback(async () => {
    const id = activeRequestRef.current;
    if (!id) return;
    try {
      await cancelVaultSidecarTask(id);
    } catch (nextError) {
      setError({
        code: "cancel_failed",
        message: nextError instanceof Error ? nextError.message : String(nextError),
        retryable: true,
      });
    }
  }, []);

  const handleClose = useCallback(() => {
    if (activeRequestRef.current) {
      const shouldCancel = window.confirm(t("vault.confirm.closeActive"));
      if (!shouldCancel) return;
      void cancelActive();
    }
    onClose();
  }, [cancelActive, onClose, t]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-h-[92vh] max-w-6xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <DatabaseBackup className="h-5 w-5" />
            {t("vault.title")}
          </DialogTitle>
          <DialogDescription>{t("vault.description")}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(340px,0.8fr)]">
          <section className="space-y-4 rounded-lg border p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">{t("vault.configuration")}</h3>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {isInitializing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : status?.available ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                )}
                <span>
                  {status?.available
                    ? t("vault.sidecarAvailable")
                    : status?.reason ?? t("vault.sidecarUnavailable")}
                </span>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <Field label={t("vault.fields.application")}>
                <select
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                  value={config.selectedAppId}
                  onChange={(event) =>
                    updateConfig("selectedAppId", event.target.value)
                  }
                  disabled={Boolean(activeRequestId)}
                >
                  {adapters.length === 0 && (
                    <option value={config.selectedAppId}>
                      {config.selectedAppId || t("vault.loadingApplications")}
                    </option>
                  )}
                  {adapters.map((adapter) => (
                    <option key={adapter.app_id} value={adapter.app_id}>
                      {adapter.display_name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t("vault.fields.machineId")}>
                <Input
                  value={config.machineId}
                  onChange={(event) => updateConfig("machineId", event.target.value)}
                  placeholder={t("vault.placeholders.machineId")}
                />
              </Field>
              <Field label={t("vault.fields.vaultRoot")} className="md:col-span-2">
                <Input
                  value={config.vaultRoot}
                  onChange={(event) => updateConfig("vaultRoot", event.target.value)}
                  placeholder="D:\\AI-Session-Vault"
                />
              </Field>
              <Field label={t("vault.fields.sourceRoot")} className="md:col-span-2">
                <Input
                  value={config.sourceRoot}
                  onChange={(event) => updateConfig("sourceRoot", event.target.value)}
                  placeholder={
                    selectedAdapter?.default_source_root ??
                    t("vault.placeholders.sourceRoot")
                  }
                />
              </Field>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() => void runOperation("inspect")}
                disabled={!status?.available || Boolean(activeRequestId)}
              >
                <FolderSearch className="mr-2 h-4 w-4" />
                {t("vault.actions.inspect")}
              </Button>
              <Button
                variant="outline"
                onClick={() => void runOperation("layout")}
                disabled={!status?.available || Boolean(activeRequestId)}
              >
                {t("vault.actions.layout")}
              </Button>
              <Button
                variant="outline"
                onClick={() => void runOperation("sync", true)}
                disabled={!status?.available || Boolean(activeRequestId)}
              >
                {t("vault.actions.previewBackup")}
              </Button>
              <Button
                onClick={() => void runOperation("sync")}
                disabled={!status?.available || Boolean(activeRequestId)}
              >
                <Play className="mr-2 h-4 w-4" />
                {t("vault.actions.backup")}
              </Button>
              <Button
                variant="outline"
                onClick={() => void runOperation("verify")}
                disabled={!status?.available || Boolean(activeRequestId)}
              >
                <ShieldCheck className="mr-2 h-4 w-4" />
                {t("vault.actions.verify")}
              </Button>
            </div>

            <div className="space-y-3 rounded-md border border-dashed p-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">{t("vault.restore.title")}</h4>
                {!canRestore && (
                  <span className="text-xs text-muted-foreground">
                    {t("vault.restore.unsupported")}
                  </span>
                )}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Field label={t("vault.fields.restoreScope")}>
                  <select
                    className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                    value={config.restoreScope}
                    onChange={(event) =>
                      updateConfig(
                        "restoreScope",
                        event.target.value === "full" ? "full" : "session",
                      )
                    }
                  >
                    <option value="session">{t("vault.restore.session")}</option>
                    <option value="full">{t("vault.restore.full")}</option>
                  </select>
                </Field>
                <Field label={t("vault.fields.sessionId")}>
                  <Input
                    value={config.sessionId}
                    onChange={(event) => updateConfig("sessionId", event.target.value)}
                    disabled={config.restoreScope === "full"}
                    placeholder={t("vault.placeholders.sessionId")}
                  />
                </Field>
                <Field label={t("vault.fields.restoreRoot")} className="md:col-span-2">
                  <Input
                    value={config.restoreRoot}
                    onChange={(event) =>
                      updateConfig("restoreRoot", event.target.value)
                    }
                    placeholder="D:\\Codex-Recovery"
                  />
                </Field>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  onClick={() => void runOperation("restore", true)}
                  disabled={!canRestore || Boolean(activeRequestId)}
                >
                  {t("vault.actions.previewRestore")}
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => void runOperation("restore")}
                  disabled={!canRestore || Boolean(activeRequestId)}
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  {t("vault.actions.restore")}
                </Button>
              </div>
            </div>
          </section>

          <section className="space-y-4 rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">{t("vault.task.title")}</h3>
              {activeRequestId && (
                <Button variant="outline" size="sm" onClick={() => void cancelActive()}>
                  <Square className="mr-2 h-3.5 w-3.5" />
                  {t("vault.actions.cancel")}
                </Button>
              )}
            </div>

            {activeOperation && (
              <div className="space-y-2 rounded-md bg-muted/50 p-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("vault.task.running", { operation: activeOperation })}
                </div>
                {progress && (
                  <>
                    <p className="text-xs text-muted-foreground">{progress.message}</p>
                    {percent != null && (
                      <div className="h-2 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full bg-primary transition-[width]"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {progress.stage}
                      {progress.current != null && progress.total != null
                        ? ` · ${progress.current}/${progress.total}`
                        : ""}
                    </p>
                  </>
                )}
              </div>
            )}

            {error && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3">
                <div className="flex items-center gap-2 text-sm font-medium text-destructive">
                  <AlertTriangle className="h-4 w-4" />
                  {error.code}
                </div>
                <p className="mt-1 text-xs text-destructive/90">{error.message}</p>
              </div>
            )}

            {result != null && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                  {t("vault.task.completed")}
                </div>
                {reportPath && (
                  <p className="break-all rounded bg-muted px-2 py-1 text-xs">
                    {t("vault.task.output")}: {reportPath}
                  </p>
                )}
                <pre className="max-h-72 overflow-auto rounded-md bg-muted p-3 text-xs">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}

            {preview && (
              <details className="rounded-md border p-2 text-xs">
                <summary className="cursor-pointer font-medium">
                  {t("vault.task.commandPreview")}
                </summary>
                <pre className="mt-2 overflow-auto whitespace-pre-wrap break-all text-muted-foreground">
                  {[preview.program, ...preview.args].join(" ")}
                </pre>
              </details>
            )}

            <details className="rounded-md border p-2 text-xs">
              <summary className="cursor-pointer font-medium">
                {t("vault.task.events")} ({events.length})
              </summary>
              <div className="mt-2 max-h-52 space-y-1 overflow-auto">
                {events.length === 0 ? (
                  <p className="text-muted-foreground">{t("vault.task.noEvents")}</p>
                ) : (
                  events.map((event) => {
                    const eventProgress = asProgress(event.data);
                    return (
                      <div
                        key={`${event.request_id}-${event.sequence}`}
                        className="rounded bg-muted/60 px-2 py-1"
                      >
                        <span className="font-mono">#{event.sequence}</span>{" "}
                        <span>{event.event}</span>
                        {eventProgress?.message ? ` · ${eventProgress.message}` : ""}
                      </div>
                    );
                  })
                )}
              </div>
            </details>

            {tasks.length > 0 && (
              <div className="space-y-1 text-xs text-muted-foreground">
                <p className="font-medium text-foreground">{t("vault.task.recent")}</p>
                {tasks.slice(0, 5).map((task) => (
                  <p key={task.requestId}>
                    {task.operation} · {task.status} · {task.requestId.slice(0, 8)}
                  </p>
                ))}
              </div>
            )}
          </section>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            {t("vault.actions.close")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  children,
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}

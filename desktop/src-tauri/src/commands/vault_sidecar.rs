use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tauri::{AppHandle, Emitter, State};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

pub const SIDECAR_PROTOCOL_NAME: &str = "ai-session-vault-sidecar";
pub const SIDECAR_PROTOCOL_VERSION: u32 = 1;
pub const SIDECAR_EVENT_NAME: &str = "vault-sidecar-event";
const SIDECAR_ENV: &str = "AI_SESSION_VAULT_SIDECAR";
const PYTHON_ENV: &str = "AI_SESSION_VAULT_PYTHON";
const MAX_TIMEOUT_SECONDS: u64 = 24 * 60 * 60;
const ALLOWED_OPERATIONS: [&str; 6] = [
    "list-apps",
    "inspect",
    "layout",
    "sync",
    "verify",
    "restore",
];
const ALLOWED_EVENTS: [&str; 4] = ["started", "progress", "completed", "failed"];

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VaultSidecarError {
    pub code: String,
    pub message: String,
    pub retryable: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub details: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VaultSidecarEvent {
    pub protocol: String,
    pub protocol_version: u32,
    pub request_id: String,
    pub sequence: u64,
    pub timestamp: String,
    pub operation: String,
    pub event: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<VaultSidecarError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct VaultSidecarRequest {
    pub operation: String,
    #[serde(default)]
    pub app_id: Option<String>,
    #[serde(default)]
    pub vault_root: Option<String>,
    #[serde(default)]
    pub source_root: Option<String>,
    #[serde(default)]
    pub machine_id: Option<String>,
    #[serde(default)]
    pub restore_root: Option<String>,
    #[serde(default)]
    pub restore_scope: Option<String>,
    #[serde(default)]
    pub session_id: Option<String>,
    #[serde(default)]
    pub dry_run: bool,
    #[serde(default)]
    pub request_id: Option<String>,
    #[serde(default)]
    pub timeout_seconds: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VaultSidecarStatus {
    pub available: bool,
    pub protocol: &'static str,
    pub protocol_version: u32,
    pub entrypoint: String,
    pub program: String,
    pub launch_mode: String,
    pub reason: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VaultSidecarCommandPreview {
    pub program: String,
    pub args: Vec<String>,
    pub request_id: String,
    pub operation: String,
    pub protocol: &'static str,
    pub protocol_version: u32,
    pub timeout_seconds: u64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VaultSidecarTaskStart {
    pub request_id: String,
    pub operation: String,
    pub timeout_seconds: u64,
    pub started_at: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VaultSidecarTaskInfo {
    pub request_id: String,
    pub operation: String,
    pub started_at: String,
    pub timeout_seconds: u64,
    pub cancel_requested: bool,
    pub status: String,
}

struct RunningTask {
    operation: String,
    started_at: String,
    timeout_seconds: u64,
    child: Mutex<Option<Child>>,
    cancel_requested: AtomicBool,
    terminal_seen: AtomicBool,
    last_sequence: AtomicU64,
}

impl RunningTask {
    fn info(&self, request_id: &str) -> VaultSidecarTaskInfo {
        VaultSidecarTaskInfo {
            request_id: request_id.to_string(),
            operation: self.operation.clone(),
            started_at: self.started_at.clone(),
            timeout_seconds: self.timeout_seconds,
            cancel_requested: self.cancel_requested.load(Ordering::SeqCst),
            status: if self.cancel_requested.load(Ordering::SeqCst) {
                "cancelling".to_string()
            } else {
                "running".to_string()
            },
        }
    }
}

#[derive(Clone, Default)]
pub struct VaultSidecarTaskState {
    tasks: Arc<Mutex<HashMap<String, Arc<RunningTask>>>>,
}

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn default_sidecar_entrypoint() -> PathBuf {
    repository_root().join("scripts").join("vault_sync.py")
}

fn sidecar_entrypoint() -> PathBuf {
    std::env::var_os(SIDECAR_ENV)
        .map(PathBuf::from)
        .unwrap_or_else(default_sidecar_entrypoint)
}

fn is_python_script(path: &Path) -> bool {
    path.extension()
        .and_then(|value| value.to_str())
        .is_some_and(|value| value.eq_ignore_ascii_case("py"))
}

fn now_timestamp() -> String {
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    format!("{}.{:03}Z", duration.as_secs(), duration.subsec_millis())
}

fn validate_text(value: &str, label: &str) -> Result<(), String> {
    if value.trim().is_empty() {
        return Err(format!("{label} must not be empty"));
    }
    if value.contains('\0') {
        return Err(format!("{label} must not contain NUL characters"));
    }
    Ok(())
}

fn required<'a>(value: &'a Option<String>, label: &str) -> Result<&'a str, String> {
    let value = value
        .as_deref()
        .ok_or_else(|| format!("{label} is required"))?;
    validate_text(value, label)?;
    Ok(value)
}

fn optional<'a>(value: &'a Option<String>, label: &str) -> Result<Option<&'a str>, String> {
    match value.as_deref() {
        Some(value) => {
            validate_text(value, label)?;
            Ok(Some(value))
        }
        None => Ok(None),
    }
}

fn default_timeout_seconds(operation: &str) -> u64 {
    match operation {
        "list-apps" | "inspect" | "layout" => 120,
        "verify" => 10 * 60,
        "sync" | "restore" => 60 * 60,
        _ => 5 * 60,
    }
}

fn resolved_timeout_seconds(request: &VaultSidecarRequest) -> Result<u64, String> {
    let timeout = request
        .timeout_seconds
        .unwrap_or_else(|| default_timeout_seconds(&request.operation));
    if timeout == 0 || timeout > MAX_TIMEOUT_SECONDS {
        return Err(format!(
            "timeoutSeconds must be between 1 and {MAX_TIMEOUT_SECONDS}"
        ));
    }
    Ok(timeout)
}

fn validate_request(request: &VaultSidecarRequest) -> Result<(), String> {
    validate_text(&request.operation, "operation")?;
    if !ALLOWED_OPERATIONS.contains(&request.operation.as_str()) {
        return Err(format!(
            "unsupported operation: {}; expected one of {}",
            request.operation,
            ALLOWED_OPERATIONS.join(", ")
        ));
    }

    if request.operation != "list-apps" {
        required(&request.app_id, "appId")?;
    } else if request.app_id.is_some() {
        optional(&request.app_id, "appId")?;
    }

    optional(&request.source_root, "sourceRoot")?;
    optional(&request.machine_id, "machineId")?;
    optional(&request.request_id, "requestId")?;

    if matches!(
        request.operation.as_str(),
        "layout" | "sync" | "verify" | "restore"
    ) {
        required(&request.vault_root, "vaultRoot")?;
    } else {
        optional(&request.vault_root, "vaultRoot")?;
    }

    if request.operation == "restore" {
        required(&request.restore_root, "restoreRoot")?;
        let scope = request.restore_scope.as_deref().unwrap_or("session");
        if !matches!(scope, "session" | "full") {
            return Err("restoreScope must be session or full".to_string());
        }
        if scope == "session" {
            required(&request.session_id, "sessionId")?;
        } else {
            optional(&request.session_id, "sessionId")?;
        }
    } else {
        optional(&request.restore_root, "restoreRoot")?;
        optional(&request.restore_scope, "restoreScope")?;
        optional(&request.session_id, "sessionId")?;
    }

    resolved_timeout_seconds(request)?;
    Ok(())
}

fn push_option(args: &mut Vec<String>, flag: &str, value: Option<&str>) {
    if let Some(value) = value {
        args.push(flag.to_string());
        args.push(value.to_string());
    }
}

fn build_command_preview(
    request: VaultSidecarRequest,
) -> Result<VaultSidecarCommandPreview, String> {
    validate_request(&request)?;
    let entrypoint = sidecar_entrypoint();
    if !entrypoint.is_file() {
        return Err(format!(
            "Vault Core sidecar entrypoint does not exist: {}",
            entrypoint.display()
        ));
    }

    let request_id = request
        .request_id
        .clone()
        .unwrap_or_else(|| uuid::Uuid::new_v4().simple().to_string());
    let python_script = is_python_script(&entrypoint);
    let program = if python_script {
        std::env::var(PYTHON_ENV).unwrap_or_else(|_| "python".to_string())
    } else {
        entrypoint.to_string_lossy().into_owned()
    };
    validate_text(&program, "sidecar program")?;

    let mut args = Vec::new();
    if python_script {
        args.push(entrypoint.to_string_lossy().into_owned());
    }
    args.extend([
        "--mode".to_string(),
        request.operation.clone(),
        "--output-format".to_string(),
        "jsonl".to_string(),
        "--protocol-version".to_string(),
        SIDECAR_PROTOCOL_VERSION.to_string(),
        "--request-id".to_string(),
        request_id.clone(),
    ]);
    push_option(&mut args, "--app", request.app_id.as_deref());
    push_option(&mut args, "--vault-root", request.vault_root.as_deref());
    push_option(&mut args, "--source-root", request.source_root.as_deref());
    push_option(&mut args, "--machine-id", request.machine_id.as_deref());
    push_option(&mut args, "--restore-root", request.restore_root.as_deref());
    if request.operation == "restore" {
        push_option(
            &mut args,
            "--restore-scope",
            Some(request.restore_scope.as_deref().unwrap_or("session")),
        );
        push_option(&mut args, "--session-id", request.session_id.as_deref());
    }
    if request.dry_run {
        args.push("--dry-run".to_string());
    }

    Ok(VaultSidecarCommandPreview {
        program,
        args,
        request_id,
        operation: request.operation,
        protocol: SIDECAR_PROTOCOL_NAME,
        protocol_version: SIDECAR_PROTOCOL_VERSION,
        timeout_seconds: resolved_timeout_seconds(&request)?,
    })
}

pub fn parse_sidecar_event(
    line: &str,
    expected_request_id: &str,
    expected_operation: &str,
    previous_sequence: Option<u64>,
) -> Result<VaultSidecarEvent, String> {
    let event: VaultSidecarEvent =
        serde_json::from_str(line).map_err(|error| format!("invalid sidecar JSON: {error}"))?;
    if event.protocol != SIDECAR_PROTOCOL_NAME {
        return Err(format!("unexpected sidecar protocol: {}", event.protocol));
    }
    if event.protocol_version != SIDECAR_PROTOCOL_VERSION {
        return Err(format!(
            "unsupported sidecar protocol version: {}",
            event.protocol_version
        ));
    }
    if event.request_id != expected_request_id {
        return Err("sidecar requestId does not match the active task".to_string());
    }
    if event.operation != expected_operation {
        return Err("sidecar operation does not match the active task".to_string());
    }
    if !ALLOWED_EVENTS.contains(&event.event.as_str()) {
        return Err(format!("unsupported sidecar event: {}", event.event));
    }
    if event.sequence == 0 || previous_sequence.is_some_and(|value| event.sequence <= value) {
        return Err("sidecar sequence must increase monotonically".to_string());
    }
    if event.event == "failed" && event.error.is_none() {
        return Err("failed sidecar event is missing error details".to_string());
    }
    if event.event != "failed" && event.error.is_some() {
        return Err("non-failed sidecar event contains error details".to_string());
    }
    Ok(event)
}

fn synthetic_failed_event(
    task: &RunningTask,
    request_id: &str,
    code: &str,
    message: String,
    retryable: bool,
    details: Option<Value>,
) -> VaultSidecarEvent {
    let sequence = task.last_sequence.fetch_add(1, Ordering::SeqCst) + 1;
    task.terminal_seen.store(true, Ordering::SeqCst);
    VaultSidecarEvent {
        protocol: SIDECAR_PROTOCOL_NAME.to_string(),
        protocol_version: SIDECAR_PROTOCOL_VERSION,
        request_id: request_id.to_string(),
        sequence,
        timestamp: now_timestamp(),
        operation: task.operation.clone(),
        event: "failed".to_string(),
        data: None,
        error: Some(VaultSidecarError {
            code: code.to_string(),
            message,
            retryable,
            details,
        }),
    }
}

fn emit_event(app: &AppHandle, event: VaultSidecarEvent) {
    if let Err(error) = app.emit(SIDECAR_EVENT_NAME, event) {
        log::error!("failed to emit Vault Sidecar event: {error}");
    }
}

fn monitor_task(
    app: AppHandle,
    state: VaultSidecarTaskState,
    request_id: String,
    task: Arc<RunningTask>,
    stdout: impl Read + Send + 'static,
    stderr: impl Read + Send + 'static,
) {
    let stdout_task = Arc::clone(&task);
    let stdout_app = app.clone();
    let stdout_request_id = request_id.clone();
    let protocol_error: Arc<Mutex<Option<String>>> = Arc::new(Mutex::new(None));
    let protocol_error_reader = Arc::clone(&protocol_error);

    let stdout_thread = thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            let line = match line {
                Ok(line) => line,
                Err(error) => {
                    *protocol_error_reader.lock().expect("protocol error lock poisoned") =
                        Some(format!("failed reading sidecar stdout: {error}"));
                    break;
                }
            };
            if line.trim().is_empty() {
                continue;
            }
            let previous = stdout_task.last_sequence.load(Ordering::SeqCst);
            match parse_sidecar_event(
                &line,
                &stdout_request_id,
                &stdout_task.operation,
                (previous > 0).then_some(previous),
            ) {
                Ok(event) => {
                    stdout_task
                        .last_sequence
                        .store(event.sequence, Ordering::SeqCst);
                    if matches!(event.event.as_str(), "completed" | "failed") {
                        stdout_task.terminal_seen.store(true, Ordering::SeqCst);
                    }
                    emit_event(&stdout_app, event);
                }
                Err(error) => {
                    *protocol_error_reader.lock().expect("protocol error lock poisoned") =
                        Some(error);
                    break;
                }
            }
        }
    });

    let stderr_thread = thread::spawn(move || {
        let mut reader = BufReader::new(stderr);
        let mut output = String::new();
        let _ = reader.read_to_string(&mut output);
        output
    });

    let started = Instant::now();
    let mut timed_out = false;
    let mut exit_status: Option<ExitStatus> = None;

    while exit_status.is_none() {
        if started.elapsed() >= Duration::from_secs(task.timeout_seconds) {
            timed_out = true;
            task.cancel_requested.store(true, Ordering::SeqCst);
        }

        let mut child_guard = task.child.lock().expect("sidecar child lock poisoned");
        if let Some(child) = child_guard.as_mut() {
            if task.cancel_requested.load(Ordering::SeqCst) {
                let _ = child.kill();
            }
            match child.try_wait() {
                Ok(status) => exit_status = status,
                Err(error) => {
                    if !task.terminal_seen.swap(true, Ordering::SeqCst) {
                        emit_event(
                            &app,
                            synthetic_failed_event(
                                &task,
                                &request_id,
                                "process_wait_failed",
                                format!("failed waiting for sidecar process: {error}"),
                                true,
                                None,
                            ),
                        );
                    }
                    break;
                }
            }
        } else {
            break;
        }
        drop(child_guard);
        if exit_status.is_none() {
            thread::sleep(Duration::from_millis(100));
        }
    }

    let _ = stdout_thread.join();
    let stderr_output = stderr_thread.join().unwrap_or_default();

    if !task.terminal_seen.load(Ordering::SeqCst) {
        let protocol_failure = protocol_error
            .lock()
            .expect("protocol error lock poisoned")
            .clone();
        let (code, message, retryable, details) = if let Some(error) = protocol_failure {
            (
                "protocol_error",
                error,
                false,
                Some(json!({"stderr": stderr_output.trim()})),
            )
        } else if timed_out {
            (
                "timeout",
                format!("sidecar exceeded {} seconds", task.timeout_seconds),
                true,
                Some(json!({"stderr": stderr_output.trim()})),
            )
        } else if task.cancel_requested.load(Ordering::SeqCst) {
            (
                "cancelled",
                "sidecar task was cancelled".to_string(),
                true,
                Some(json!({"stderr": stderr_output.trim()})),
            )
        } else if let Some(status) = exit_status {
            if status.success() {
                (
                    "missing_terminal_event",
                    "sidecar exited successfully without a completed or failed event".to_string(),
                    false,
                    Some(json!({"stderr": stderr_output.trim()})),
                )
            } else {
                (
                    "process_exit",
                    format!("sidecar exited with status {status}"),
                    true,
                    Some(json!({"stderr": stderr_output.trim()})),
                )
            }
        } else {
            (
                "process_ended",
                "sidecar process ended without a terminal event".to_string(),
                true,
                Some(json!({"stderr": stderr_output.trim()})),
            )
        };
        emit_event(
            &app,
            synthetic_failed_event(&task, &request_id, code, message, retryable, details),
        );
    }

    if let Ok(mut tasks) = state.tasks.lock() {
        tasks.remove(&request_id);
    }
}

#[tauri::command]
pub fn get_vault_sidecar_status() -> VaultSidecarStatus {
    let entrypoint = sidecar_entrypoint();
    let launch_mode = if is_python_script(&entrypoint) {
        "python-script"
    } else {
        "executable"
    };
    let program = if launch_mode == "python-script" {
        std::env::var(PYTHON_ENV).unwrap_or_else(|_| "python".to_string())
    } else {
        entrypoint.to_string_lossy().into_owned()
    };
    let entrypoint_available = entrypoint.is_file();
    let program_available = if entrypoint_available && launch_mode == "python-script" {
        Command::new(&program)
            .arg("--version")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .is_ok()
    } else {
        entrypoint_available
    };
    let available = entrypoint_available && program_available;
    let reason = if !entrypoint_available {
        Some(format!(
            "Vault Core sidecar entrypoint does not exist: {}",
            entrypoint.display()
        ))
    } else if !program_available {
        Some(format!(
            "Vault Core requires an available Python runtime. Set {PYTHON_ENV} to the executable path."
        ))
    } else {
        None
    };

    VaultSidecarStatus {
        available,
        protocol: SIDECAR_PROTOCOL_NAME,
        protocol_version: SIDECAR_PROTOCOL_VERSION,
        entrypoint: entrypoint.to_string_lossy().into_owned(),
        program,
        launch_mode: launch_mode.to_string(),
        reason,
    }
}

#[tauri::command]
pub fn preview_vault_sidecar_command(
    request: VaultSidecarRequest,
) -> Result<VaultSidecarCommandPreview, String> {
    build_command_preview(request)
}

#[tauri::command]
pub fn start_vault_sidecar_task(
    app: AppHandle,
    state: State<'_, VaultSidecarTaskState>,
    request: VaultSidecarRequest,
) -> Result<VaultSidecarTaskStart, String> {
    let preview = build_command_preview(request)?;
    let state = state.inner().clone();
    {
        let tasks = state
            .tasks
            .lock()
            .map_err(|_| "Vault task registry lock is poisoned".to_string())?;
        if tasks.contains_key(&preview.request_id) {
            return Err(format!(
                "Vault task requestId is already active: {}",
                preview.request_id
            ));
        }
    }

    let mut command = Command::new(&preview.program);
    command
        .args(&preview.args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(target_os = "windows")]
    command.creation_flags(CREATE_NO_WINDOW);

    let mut child = command
        .spawn()
        .map_err(|error| format!("failed to start Vault Core sidecar: {error}"))?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "failed to capture sidecar stdout".to_string())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "failed to capture sidecar stderr".to_string())?;
    let started_at = now_timestamp();
    let task = Arc::new(RunningTask {
        operation: preview.operation.clone(),
        started_at: started_at.clone(),
        timeout_seconds: preview.timeout_seconds,
        child: Mutex::new(Some(child)),
        cancel_requested: AtomicBool::new(false),
        terminal_seen: AtomicBool::new(false),
        last_sequence: AtomicU64::new(0),
    });

    state
        .tasks
        .lock()
        .map_err(|_| "Vault task registry lock is poisoned".to_string())?
        .insert(preview.request_id.clone(), Arc::clone(&task));

    let request_id = preview.request_id.clone();
    let worker_request_id = request_id.clone();
    thread::spawn(move || {
        monitor_task(app, state, worker_request_id, task, stdout, stderr);
    });

    Ok(VaultSidecarTaskStart {
        request_id,
        operation: preview.operation,
        timeout_seconds: preview.timeout_seconds,
        started_at,
    })
}

#[tauri::command]
pub fn cancel_vault_sidecar_task(
    state: State<'_, VaultSidecarTaskState>,
    request_id: String,
) -> Result<bool, String> {
    validate_text(&request_id, "requestId")?;
    let task = state
        .tasks
        .lock()
        .map_err(|_| "Vault task registry lock is poisoned".to_string())?
        .get(&request_id)
        .cloned();
    let Some(task) = task else {
        return Ok(false);
    };
    task.cancel_requested.store(true, Ordering::SeqCst);
    if let Ok(mut child_guard) = task.child.lock() {
        if let Some(child) = child_guard.as_mut() {
            let _ = child.kill();
        }
    }
    Ok(true)
}

#[tauri::command]
pub fn list_vault_sidecar_tasks(
    state: State<'_, VaultSidecarTaskState>,
) -> Result<Vec<VaultSidecarTaskInfo>, String> {
    let tasks = state
        .tasks
        .lock()
        .map_err(|_| "Vault task registry lock is poisoned".to_string())?;
    let mut values = tasks
        .iter()
        .map(|(request_id, task)| task.info(request_id))
        .collect::<Vec<_>>();
    values.sort_by(|left, right| left.started_at.cmp(&right.started_at));
    Ok(values)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(operation: &str) -> VaultSidecarRequest {
        VaultSidecarRequest {
            operation: operation.to_string(),
            app_id: None,
            vault_root: None,
            source_root: None,
            machine_id: None,
            restore_root: None,
            restore_scope: None,
            session_id: None,
            dry_run: false,
            request_id: Some("request-1".to_string()),
            timeout_seconds: None,
        }
    }

    #[test]
    fn validates_operation_specific_requirements() {
        assert!(validate_request(&request("list-apps")).is_ok());

        let mut sync = request("sync");
        sync.app_id = Some("codex".to_string());
        assert_eq!(
            validate_request(&sync).unwrap_err(),
            "vaultRoot is required"
        );

        let mut restore = request("restore");
        restore.app_id = Some("codex".to_string());
        restore.vault_root = Some("E:/Vault".to_string());
        restore.restore_root = Some("E:/Recovery".to_string());
        assert_eq!(
            validate_request(&restore).unwrap_err(),
            "sessionId is required"
        );
    }

    #[test]
    fn rejects_nul_characters_before_process_launch() {
        let mut inspect = request("inspect");
        inspect.app_id = Some("codex\0bad".to_string());
        assert_eq!(
            validate_request(&inspect).unwrap_err(),
            "appId must not contain NUL characters"
        );
    }

    #[test]
    fn validates_timeout_range() {
        let mut inspect = request("inspect");
        inspect.app_id = Some("codex".to_string());
        inspect.timeout_seconds = Some(0);
        assert!(validate_request(&inspect).is_err());
        inspect.timeout_seconds = Some(MAX_TIMEOUT_SECONDS + 1);
        assert!(validate_request(&inspect).is_err());
    }

    #[test]
    fn parses_and_validates_protocol_events() {
        let line = r#"{"protocol":"ai-session-vault-sidecar","protocol_version":1,"request_id":"request-1","sequence":2,"timestamp":"2026-07-24T00:00:00Z","operation":"sync","event":"completed","data":{"ok":true}}"#;
        let event = parse_sidecar_event(line, "request-1", "sync", Some(1)).unwrap();
        assert_eq!(event.event, "completed");
        assert_eq!(event.sequence, 2);
    }

    #[test]
    fn rejects_replayed_or_mismatched_events() {
        let line = r#"{"protocol":"ai-session-vault-sidecar","protocol_version":1,"request_id":"other","sequence":1,"timestamp":"2026-07-24T00:00:00Z","operation":"sync","event":"started"}"#;
        assert!(parse_sidecar_event(line, "request-1", "sync", None).is_err());

        let line = r#"{"protocol":"ai-session-vault-sidecar","protocol_version":1,"request_id":"request-1","sequence":1,"timestamp":"2026-07-24T00:00:00Z","operation":"sync","event":"progress","data":{}}"#;
        assert!(parse_sidecar_event(line, "request-1", "sync", Some(1)).is_err());
    }
}

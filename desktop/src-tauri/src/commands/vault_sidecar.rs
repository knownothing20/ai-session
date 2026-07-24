use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::{Path, PathBuf};

pub const SIDECAR_PROTOCOL_NAME: &str = "ai-session-vault-sidecar";
pub const SIDECAR_PROTOCOL_VERSION: u32 = 1;
const SIDECAR_ENV: &str = "AI_SESSION_VAULT_SIDECAR";
const PYTHON_ENV: &str = "AI_SESSION_VAULT_PYTHON";
const ALLOWED_OPERATIONS: [&str; 6] = [
    "list-apps",
    "inspect",
    "layout",
    "sync",
    "verify",
    "restore",
];
const ALLOWED_EVENTS: [&str; 4] = ["started", "progress", "completed", "failed"];

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
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VaultSidecarStatus {
    pub available: bool,
    pub protocol: &'static str,
    pub protocol_version: u32,
    pub entrypoint: String,
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

#[tauri::command]
pub fn get_vault_sidecar_status() -> VaultSidecarStatus {
    let entrypoint = sidecar_entrypoint();
    let available = entrypoint.is_file();
    VaultSidecarStatus {
        available,
        protocol: SIDECAR_PROTOCOL_NAME,
        protocol_version: SIDECAR_PROTOCOL_VERSION,
        entrypoint: entrypoint.to_string_lossy().into_owned(),
        launch_mode: if is_python_script(&entrypoint) {
            "python-script".to_string()
        } else {
            "executable".to_string()
        },
        reason: (!available).then(|| {
            "Vault Core is unavailable. Set AI_SESSION_VAULT_SIDECAR or use the monorepo development layout."
                .to_string()
        }),
    }
}

#[tauri::command]
pub fn preview_vault_sidecar_command(
    request: VaultSidecarRequest,
) -> Result<VaultSidecarCommandPreview, String> {
    build_command_preview(request)
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

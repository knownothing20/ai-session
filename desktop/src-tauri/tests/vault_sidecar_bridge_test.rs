use claude_code_history_viewer_lib::commands::vault_sidecar::{
    get_vault_sidecar_status, preview_vault_sidecar_command, VaultSidecarRequest,
    SIDECAR_PROTOCOL_NAME, SIDECAR_PROTOCOL_VERSION,
};

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
        request_id: Some("integration-request".to_string()),
        timeout_seconds: Some(30),
    }
}

#[test]
fn public_status_resolves_monorepo_sidecar() {
    let status = get_vault_sidecar_status();
    assert_eq!(status.protocol, SIDECAR_PROTOCOL_NAME);
    assert_eq!(status.protocol_version, SIDECAR_PROTOCOL_VERSION);
    assert!(status.entrypoint.ends_with("scripts/vault_sync.py"));
    assert_eq!(status.launch_mode, "python-script");
}

#[test]
fn public_preview_builds_shell_free_jsonl_arguments() {
    let mut request = request("sync");
    request.app_id = Some("codex".to_string());
    request.vault_root = Some("D:/Vault With Spaces".to_string());
    request.machine_id = Some("main-pc".to_string());
    request.dry_run = true;

    let preview = preview_vault_sidecar_command(request).unwrap();
    assert_eq!(preview.operation, "sync");
    assert_eq!(preview.request_id, "integration-request");
    assert_eq!(preview.timeout_seconds, 30);
    assert!(preview.args.windows(2).any(|pair| pair == ["--output-format", "jsonl"]));
    assert!(preview.args.windows(2).any(|pair| pair == ["--vault-root", "D:/Vault With Spaces"]));
    assert!(preview.args.iter().any(|value| value == "--dry-run"));
    assert!(!preview.args.iter().any(|value| value.contains("cmd /C")));
    assert!(!preview.args.iter().any(|value| value.contains("powershell")));
}

#[test]
fn public_preview_rejects_incomplete_restore() {
    let mut request = request("restore");
    request.app_id = Some("codex".to_string());
    request.vault_root = Some("D:/Vault".to_string());
    request.restore_root = Some("D:/Recovery".to_string());

    let error = preview_vault_sidecar_command(request).unwrap_err();
    assert_eq!(error, "sessionId is required");
}

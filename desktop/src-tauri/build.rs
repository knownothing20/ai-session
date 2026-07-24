use std::env;
use std::fs;
use std::path::PathBuf;

const HANDLER_ANCHOR: &str = "            force_quit_and_relaunch\n";
const HANDLER_REPLACEMENT: &str = concat!(
    "            force_quit_and_relaunch,\n",
    "            crate::commands::vault_sidecar::get_vault_sidecar_status,\n",
    "            crate::commands::vault_sidecar::preview_vault_sidecar_command,\n",
    "            crate::commands::vault_sidecar::start_vault_sidecar_task,\n",
    "            crate::commands::vault_sidecar::cancel_vault_sidecar_task,\n",
    "            crate::commands::vault_sidecar::list_vault_sidecar_tasks\n",
);

fn main() {
    println!("cargo:rerun-if-changed=src/lib_upstream.rs");
    println!("cargo:rerun-if-changed=src/commands/vault_sidecar.rs");

    let upstream_path = PathBuf::from("src/lib_upstream.rs");
    let upstream = fs::read_to_string(&upstream_path)
        .unwrap_or_else(|error| panic!("failed reading {}: {error}", upstream_path.display()));
    let anchor_count = upstream.matches(HANDLER_ANCHOR).count();
    assert_eq!(
        anchor_count, 1,
        "expected exactly one Tauri handler anchor in {}, found {anchor_count}; update the Stage 1 injection when syncing upstream",
        upstream_path.display()
    );
    let generated = upstream.replacen(HANDLER_ANCHOR, HANDLER_REPLACEMENT, 1);
    let output = PathBuf::from(env::var_os("OUT_DIR").expect("OUT_DIR is unavailable"))
        .join("ai_session_runtime.rs");
    fs::write(&output, generated)
        .unwrap_or_else(|error| panic!("failed writing {}: {error}", output.display()));

    tauri_build::build();
}

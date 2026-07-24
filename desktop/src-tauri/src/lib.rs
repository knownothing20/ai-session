// AI Session Vault keeps the imported CCHV runtime in lib_upstream.rs and
// injects project-specific Tauri commands through this thin wrapper. This
// minimizes upstream merge conflicts while preserving the original runtime.
extern crate tauri as upstream_tauri;

#[macro_export]
macro_rules! ai_session_generate_handler {
    ($($command:path),* $(,)?) => {
        $crate::upstream_tauri::generate_handler![
            $($command,)*
            $crate::commands::vault_sidecar::get_vault_sidecar_status,
            $crate::commands::vault_sidecar::preview_vault_sidecar_command,
            $crate::commands::vault_sidecar::start_vault_sidecar_task,
            $crate::commands::vault_sidecar::cancel_vault_sidecar_task,
            $crate::commands::vault_sidecar::list_vault_sidecar_tasks
        ]
    };
}

// The imported runtime references `tauri::...`. Re-exporting the upstream
// crate here lets us override only generate_handler while forwarding every
// other type, trait, attribute and macro unchanged.
mod tauri {
    pub use crate::ai_session_generate_handler as generate_handler;
    pub use crate::upstream_tauri::*;
}

include!("lib_upstream.rs");

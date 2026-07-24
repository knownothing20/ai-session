// The imported CCHV runtime stays byte-for-byte in lib_upstream.rs. build.rs
// generates this compilation unit and injects the AI Session Vault commands at
// the single Tauri handler anchor. Upstream syncs therefore remain reviewable,
// while a changed handler shape fails loudly during the local Cargo build.
include!(concat!(env!("OUT_DIR"), "/ai_session_runtime.rs"));

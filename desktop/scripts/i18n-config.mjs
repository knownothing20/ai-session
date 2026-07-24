#!/usr/bin/env node
/**
 * Shared i18n configuration.
 * Add every namespace here so validation and type generation cover all files.
 */

export const NAMESPACES = [
  'common',
  'analytics',
  'session',
  'settings',
  'tools',
  'error',
  'message',
  'renderers',
  'update',
  'feedback',
  'recentEdits',
  'archive',
  'webui',
  'vault',
];

export const LANGUAGES = ['en', 'ko', 'ja', 'zh-CN', 'zh-TW'];

export const BASE_LANG = 'en';

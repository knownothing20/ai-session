import { beforeEach, describe, expect, it } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const configPath = path.join(__dirname, '../tauri.conf.json');

describe('AI Session Vault Tauri configuration', () => {
  let config: any;

  beforeEach(() => {
    config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  });

  describe('schema and product identity', () => {
    it('uses the Tauri v2 schema and required top-level sections', () => {
      expect(config.$schema).toBe('https://schema.tauri.app/config/2');
      for (const key of ['productName', 'version', 'identifier', 'build', 'app', 'plugins', 'bundle']) {
        expect(config).toHaveProperty(key);
      }
    });

    it('uses the AI Session Vault product identity', () => {
      expect(config.productName).toBe('AI Session Vault');
      expect(config.identifier).toBe('com.aisession.vault');
      expect(config.identifier).toMatch(/^[a-zA-Z0-9.-]+$/);
      expect(config.version).toMatch(/^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$/);
    });
  });

  describe('local development commands', () => {
    it('uses the monorepo desktop paths and Windows-compatible commands', () => {
      expect(config.build.frontendDist).toBe('../dist');
      expect(config.build.devUrl).toBe('http://localhost:1420');
      expect(config.build.beforeDevCommand).toBe('pnpm dev');
      expect(config.build.beforeBuildCommand).toBe('pnpm build');
    });

    it('uses a valid localhost development URL', () => {
      const url = new URL(config.build.devUrl);
      expect(url.protocol).toBe('http:');
      expect(url.hostname).toBe('localhost');
      expect(Number(url.port)).toBe(1420);
    });
  });

  describe('main window', () => {
    it('defines one usable primary window', () => {
      expect(Array.isArray(config.app.windows)).toBe(true);
      expect(config.app.windows.length).toBeGreaterThan(0);

      const mainWindow = config.app.windows[0];
      expect(mainWindow.label).toBe('main');
      expect(mainWindow.title).toBe('');
      expect(mainWindow.width).toBe(1200);
      expect(mainWindow.height).toBe(800);
      expect(mainWindow.minWidth).toBe(900);
      expect(mainWindow.minHeight).toBe(600);
      expect(mainWindow.resizable).toBe(true);
      expect(mainWindow.fullscreen).toBe(false);
      expect(mainWindow.center).toBe(true);
      expect(mainWindow.visible).toBe(true);
      expect(mainWindow.focus).toBe(true);
    });
  });

  describe('security and capabilities', () => {
    it('defines a restrictive CSP and known capabilities', () => {
      expect(typeof config.app.security.csp).toBe('string');
      expect(config.app.security.csp).toContain("default-src 'self'");
      expect(config.app.security.csp).toContain("frame-ancestors 'none'");
      expect(config.app.security.capabilities).toEqual(
        expect.arrayContaining(['default', 'http-requests']),
      );
      expect(config.app.withGlobalTauri).toBe(true);
    });

    it('does not embed secret material', () => {
      const serialized = JSON.stringify(config).toLowerCase();
      for (const pattern of ['password', 'private_key', 'api_key', 'credential']) {
        expect(serialized).not.toContain(pattern);
      }
    });
  });

  describe('plugins', () => {
    it('keeps file-system handling configured', () => {
      expect(config.plugins.fs.requireLiteralLeadingDot).toBe(false);
    });

    it('disables the inherited upstream updater', () => {
      expect(config.plugins.updater).toEqual({
        active: false,
        dialog: false,
      });
      expect(config.plugins.updater.endpoints).toBeUndefined();
      expect(config.plugins.updater.pubkey).toBeUndefined();
    });
  });

  describe('bundle', () => {
    it('keeps packaging enabled without updater artifacts', () => {
      expect(config.bundle.active).toBe(true);
      expect(config.bundle.targets).toBe('all');
      expect(config.bundle.createUpdaterArtifacts).toBe(false);
    });

    it('contains cross-platform icon assets', () => {
      const expectedIcons = [
        'icons/32x32.png',
        'icons/128x128.png',
        'icons/128x128@2x.png',
        'icons/icon.icns',
        'icons/icon.ico',
      ];
      expect(config.bundle.icon).toEqual(expect.arrayContaining(expectedIcons));
    });

    it('keeps the existing macOS minimum and unsigned local-build settings', () => {
      expect(config.bundle.macOS.signingIdentity).toBeNull();
      expect(config.bundle.macOS.hardenedRuntime).toBe(true);
      expect(config.bundle.macOS.minimumSystemVersion).toBe('10.13');
    });
  });
});

describe('Tauri configuration file integrity', () => {
  it('exists, is readable, and parses as JSON', () => {
    expect(fs.existsSync(configPath)).toBe(true);
    expect(() => fs.accessSync(configPath, fs.constants.R_OK)).not.toThrow();

    const content = fs.readFileSync(configPath, 'utf-8');
    expect(content.length).toBeGreaterThan(0);
    expect(() => JSON.parse(content)).not.toThrow();
  });
});

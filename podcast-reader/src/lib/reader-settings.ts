/**
 * Unified reader settings store.
 *
 * One localStorage blob (`podcast-reader:settings`, schema v1) drives:
 *   - theme (light/sepia/dark/hc)
 *   - reading font, size, line height, width
 *   - arabic overlay
 *   - drop cap
 *   - focus mode
 *
 * The early-load inline script in ThemeScript.astro applies these on
 * <html> before content renders (no FOUC). At runtime, the ReaderSettings
 * React panel and ArabicToggle use saveSettings() to update + reflect.
 *
 * Legacy migration is handled in ThemeScript so server-rendered pages
 * pick it up at first paint.
 */

export const SETTINGS_KEY = 'podcast-reader:settings';

export type ThemeName = 'light' | 'sepia' | 'dark' | 'hc';
export type FontName  = 'source-serif' | 'eb-garamond' | 'iowan' | 'inter' | 'lexend' | 'opendyslexic';
export type WidthName = 'narrow' | 'medium' | 'wide' | 'full';

export interface ReaderSettings {
  schemaVersion: 1;
  font: FontName;
  size: 16 | 18 | 19 | 21 | 23;
  lineHeight: 1.5 | 1.7 | 1.9;
  width: WidthName;
  theme: ThemeName;
  arabicOverlay: boolean;
  dropCap: boolean;
  focusMode: boolean;
}

export const defaultSettings: ReaderSettings = {
  schemaVersion: 1,
  font: 'source-serif',
  size: 19,
  lineHeight: 1.7,
  width: 'wide',
  theme: 'light',
  arabicOverlay: false,
  dropCap: true,
  focusMode: false,
};

export function loadSettings(): ReaderSettings {
  if (typeof window === 'undefined') return defaultSettings;
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY);
    if (!raw) return defaultSettings;
    const parsed = JSON.parse(raw);
    if (parsed?.schemaVersion === 1) return { ...defaultSettings, ...parsed };
  } catch { /* ignore */ }
  return defaultSettings;
}

export function saveSettings(patch: Partial<ReaderSettings>): ReaderSettings {
  const current = loadSettings();
  const merged: ReaderSettings = { ...current, ...patch, schemaVersion: 1 };
  try {
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(merged));
    applySettings(merged);
    window.dispatchEvent(new CustomEvent('reader-settings-changed', { detail: merged }));
  } catch { /* private mode: ignore */ }
  return merged;
}

export function resetSettings(): ReaderSettings {
  try {
    window.localStorage.removeItem(SETTINGS_KEY);
  } catch { /* ignore */ }
  applySettings(defaultSettings);
  window.dispatchEvent(new CustomEvent('reader-settings-changed', { detail: defaultSettings }));
  return defaultSettings;
}

export function applySettings(s: ReaderSettings): void {
  const h = document.documentElement;
  h.setAttribute('data-theme', s.theme);
  h.setAttribute('data-reader-font', s.font);
  h.setAttribute('data-reader-width', s.width);
  h.setAttribute('data-dropcap', s.dropCap ? 'on' : 'off');
  h.setAttribute('data-focus-mode', s.focusMode ? 'on' : 'off');
  h.style.setProperty('--reading-size', `${s.size}px`);
  h.style.setProperty('--reading-line-height', String(s.lineHeight));
  document.body.setAttribute('data-arabic', s.arabicOverlay ? 'on' : 'off');
  document.body.setAttribute('data-theme-body', s.theme);
}

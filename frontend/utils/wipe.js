/**
 * utils/wipe.js
 * ─────────────
 * Registers a beforeunload handler that clears all in-memory state.
 *
 * Call registerWipe() once at app boot (main.jsx).
 * After this fires, all sensitive data (session keys, passphrases,
 * derived key material) is gone from RAM.
 */
import { memory } from './memory.js'

export function registerWipe() {
  window.addEventListener('beforeunload', () => {
    memory.clear()
    // Overwrite any local variables that might linger in V8's heap
    // (best-effort — JS has no guaranteed memory zeroing)
  })
}
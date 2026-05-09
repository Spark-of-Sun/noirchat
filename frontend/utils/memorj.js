/**
 * utils/memory.js
 * ───────────────
 * Volatile in-memory key-value store.
 *
 * Nothing here persists after tab close.
 * No localStorage, no sessionStorage, no IndexedDB.
 * The wipe.js module zeroes all values on beforeunload.
 */

const _store = new Map()

export const memory = {
  set(key, value) {
    _store.set(key, value)
  },

  get(key) {
    return _store.get(key) ?? null
  },

  delete(key) {
    _store.delete(key)
  },

  clear() {
    _store.clear()
  },

  has(key) {
    return _store.has(key)
  },
}
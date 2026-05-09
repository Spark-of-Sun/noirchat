/**
 * utils/constants.js
 * ──────────────────
 * All configuration values in one place.
 * Change the API base URL here for different environments.
 */

export const API_BASE = import.meta.env.VITE_API_BASE ?? '/v1'

/** Argon2id parameters — must match server expectations */
export const ARGON2_PARAMS = {
  time: 3,
  memory: 65536, // 64 MB
  parallelism: 2,
  hashLen: 32,
}

/** Message payload padded to this size before encryption */
export const PAYLOAD_PAD_BYTES = 4096

/** API request timeout in milliseconds */
export const REQUEST_TIMEOUT_MS = 10_000

/** JWT storage key in memory (NOT localStorage) */
export const JWT_MEMORY_KEY = 'nc_jwt'

/** Session storage key in memory */
export const SESSION_MEMORY_KEY = 'nc_session'
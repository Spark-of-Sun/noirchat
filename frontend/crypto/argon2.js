/**
 * crypto/argon2.js
 * ─────────────────
 * Client-side Argon2id passphrase hashing using argon2-browser WASM.
 *
 * Why client-side hashing:
 *   The raw passphrase NEVER leaves the browser.
 *   The server receives only the Argon2id hash — and even that
 *   is further wrapped in a challenge-response HMAC before transmission.
 *
 * The hash output is used as input to the challenge-response derivation:
 *   session_key = HMAC-SHA256(argon2_hash, server_nonce)
 */
import argon2 from 'argon2-browser'
import { ARGON2_PARAMS } from '../utils/constants.js'

/**
 * Hash a passphrase with Argon2id.
 *
 * @param {string} passphrase - Raw passphrase entered by the user
 * @param {Uint8Array} salt   - 16-byte random salt
 * @returns {Promise<string>} - Hex-encoded 32-byte hash
 */
export async function hashPassphrase(passphrase, salt) {
  const result = await argon2.hash({
    pass: passphrase,
    salt,
    time: ARGON2_PARAMS.time,
    mem: ARGON2_PARAMS.memory,
    parallelism: ARGON2_PARAMS.parallelism,
    hashLen: ARGON2_PARAMS.hashLen,
    type: argon2.ArgonType.Argon2id,
  })
  return result.hashHex
}

/**
 * Generate a cryptographically random 16-byte salt.
 * The salt must be stored alongside the hash if the hash
 * will be re-derived later (e.g. for login).
 *
 * For sender verification: the receiver's stored hash already
 * includes its salt — the server handles verification.
 * The sender only needs to produce a hash the server can compare against.
 * In practice: use a fixed well-known salt for sender-side hashing,
 * OR derive deterministically from username (consistent without storage).
 *
 * @returns {Uint8Array} 16-byte salt
 */
export function generateSalt() {
  return crypto.getRandomValues(new Uint8Array(16))
}

/**
 * Derive a deterministic salt from the receiver's username.
 * Used by the sender so they produce the same hash every time
 * without needing to store a salt.
 *
 * @param {string} username
 * @returns {Promise<Uint8Array>} 16-byte deterministic salt
 */
export async function usernameSalt(username) {
  const enc = new TextEncoder()
  const data = enc.encode('noirchat:salt:' + username)
  const hashBuf = await crypto.subtle.digest('SHA-256', data)
  return new Uint8Array(hashBuf).slice(0, 16)
}
/**
 * Cryptographic utilities for the web resident client.
 *
 * IMPORTANT: This uses Web Crypto API for in-browser key generation and signing.
 * This is for TESTING ONLY — production uses hardware-bound keys via
 * react-native-biometrics on mobile devices.
 */

const QR_PAYLOAD_VERSION = "V1";

/**
 * Generate an ECC P-256 key pair using Web Crypto API.
 * Returns PEM-formatted public key and raw CryptoKey pair.
 */
export async function generateKeyPair(): Promise<{
  publicKeyPem: string;
  privateKey: CryptoKey;
  publicKey: CryptoKey;
}> {
  const keyPair = await crypto.subtle.generateKey(
    {
      name: "ECDSA",
      namedCurve: "P-256",
    },
    true,
    ["sign", "verify"],
  );

  const publicKeyPem = await exportPublicKeyPem(keyPair.publicKey);

  return {
    publicKeyPem,
    privateKey: keyPair.privateKey,
    publicKey: keyPair.publicKey,
  };
}

/**
 * Export a CryptoKey public key to PEM format.
 */
export async function exportPublicKeyPem(publicKey: CryptoKey): Promise<string> {
  const exported = await crypto.subtle.exportKey("spki", publicKey);
  const base64 = btoa(String.fromCharCode(...new Uint8Array(exported)));
  const pem = base64.match(/.{1,64}/g)?.join("\n") ?? base64;
  return `-----BEGIN PUBLIC KEY-----\n${pem}\n-----END PUBLIC KEY-----`;
}

/**
 * Sign a payload string with the hardware private key (Web Crypto in browser).
 * Returns base64-encoded signature.
 */
export async function signPayload(
  payload: string,
  privateKey: CryptoKey,
): Promise<string> {
  const encoder = new TextEncoder();
  const signature = await crypto.subtle.sign(
    {
      name: "ECDSA",
      hash: { name: "SHA-256" },
    },
    privateKey,
    encoder.encode(payload),
  );

  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}

/**
 * Build the QR payload string: V1|{resident_id}|{timestamp}|{signature_b64}
 */
export function buildQrPayload(
  residentId: string,
  timestamp: number,
  signatureB64: string,
): string {
  return `${QR_PAYLOAD_VERSION}|${residentId}|${timestamp}|${signatureB64}`;
}

/**
 * Get current Unix timestamp in seconds (floored).
 */
export function getCurrentTimestamp(): number {
  return Math.floor(Date.now() / 1000);
}

/**
 * Calculate seconds remaining until next QR rotation (30s cycle).
 */
export function getSecondsUntilRotation(): number {
  return 30 - (Math.floor(Date.now() / 1000) % 30);
}

// === Unit ===
export interface UnitCreate {
  unit_number: string;
  max_residents: number;
}

export interface UnitRead {
  id: string;
  unit_number: string;
  max_residents: number;
  current_resident_count: number;
  created_at: string;
  updated_at: string;
}

// === Resident ===
export interface ResidentCreate {
  unit_id: string;
  name: string;
}

export interface ResidentRead {
  id: string;
  unit_id: string;
  name: string;
  status: "pending" | "active" | "revoked";
  has_public_key: boolean;
  created_at: string;
  revoked_at: string | null;
}

export interface ResidentProvisionResponse {
  resident: ResidentRead;
  activation_token: string;
  expires_at: string;
}

export interface ResidentRegisterRequest {
  activation_token: string;
  public_key_pem: string;
}

// === Checker ===
export interface CheckerCreate {
  username: string;
  password: string;
  role: "guard" | "manager";
}

export interface CheckerRead {
  id: string;
  username: string;
  role: "guard" | "manager";
  is_active: boolean;
  created_at: string;
}

export interface CheckerLogin {
  username: string;
  password: string;
}

// === Admin ===
export type AdminRole = "setup_admin" | "resident_admin" | "staff_admin";

export interface AdminCreate {
  username: string;
  password: string;
  role: AdminRole;
}

export interface AdminLogin {
  username: string;
  password: string;
}

export interface AdminRead {
  id: string;
  username: string;
  role: AdminRole;
  is_active: boolean;
  created_at: string;
}

// === Access ===
export interface AccessVerifyRequest {
  qr_payload: string;
}

export interface AccessVerifyResponseGuard {
  status: "valid" | "invalid" | "expired";
}

export interface AccessVerifyResponseManager {
  status: "valid" | "invalid" | "expired";
  resident_name: string | null;
  unit: string | null;
}

export type AccessVerifyResponse = AccessVerifyResponseGuard | AccessVerifyResponseManager;

export function isManagerResponse(
  r: AccessVerifyResponse,
): r is AccessVerifyResponseManager {
  return "resident_name" in r;
}

// === Audit ===
export interface AuditLogRead {
  id: string;
  timestamp: string;
  action: string;
  actor_id: string | null;
  actor_role: string | null;
  unit_id: string | null;
  details: Record<string, unknown> | null;
}

// === Auth ===
export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
}
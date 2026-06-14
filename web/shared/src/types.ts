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
}

export interface CheckerLogin {
  username: string;
  password: string;
}

// === Admin ===
export interface AdminLogin {
  username: string;
  password: string;
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
  resident_name: string;
  unit: string;
}

// === Audit ===
export interface AuditLogRead {
  id: string;
  timestamp: string;
  action: string;
  actor_id: string;
  actor_role: string;
  unit_id: string | null;
  details: Record<string, unknown> | null;
}

// === Auth ===
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { api } from "@vista-authen/shared";
import type { UnitRead, ResidentRead } from "@vista-authen/shared";

interface DashboardProps {
  role: string;
  token: string;
  onLogout: () => void;
}

export default function Dashboard({ role, onLogout }: DashboardProps) {
  const [units, setUnits] = useState<UnitRead[]>([]);
  const [selectedUnit, setSelectedUnit] = useState<UnitRead | null>(null);
  const [residents, setResidents] = useState<ResidentRead[]>([]);
  
  // Create / Provision states
  const [residentName, setResidentName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  
  // Edit Owner contact states
  const [editingOwner, setEditingOwner] = useState<ResidentRead | null>(null);
  const [editPhone, setEditPhone] = useState("");
  const [editEmail, setEditEmail] = useState("");

  const [activationResult, setActivationResult] = useState<{
    name: string;
    token: string;
    expiresAt: string;
  } | null>(null);

  const [loadingUnits, setLoadingUnits] = useState(false);
  const [loadingResidents, setLoadingResidents] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Fetch all units
  const fetchUnits = useCallback(async () => {
    setLoadingUnits(true);
    setError("");
    try {
      const response = await api.get("/api/v1/units");
      const fetchedUnits: UnitRead[] = response.data;
      setUnits(fetchedUnits);
      
      // Keep selected unit synchronized
      if (selectedUnit) {
        const updated = fetchedUnits.find(u => u.id === selectedUnit.id);
        if (updated) setSelectedUnit(updated);
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 403) {
        setError("Your account does not have permission to view units. Requires Resident Admin or Setup Admin role.");
      } else if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to load units");
      }
    } finally {
      setLoadingUnits(false);
    }
  }, [selectedUnit]);

  // Fetch residents for a unit
  const fetchResidents = useCallback(async (unitId: string) => {
    setLoadingResidents(true);
    setResidents([]);
    setError("");
    try {
      const response = await api.get(`/api/v1/residents/by-unit/${unitId}`);
      setResidents(response.data);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to load residents for unit");
      }
    } finally {
      setLoadingResidents(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchUnits();
  }, []);

  // Load residents when unit changes
  useEffect(() => {
    if (selectedUnit) {
      fetchResidents(selectedUnit.id);
    } else {
      setResidents([]);
    }
  }, [selectedUnit?.id]);

  // Find active owner
  const activeOwner = residents.find(r => r.is_owner && r.status !== "revoked");

  // Provision resident
  const handleProvision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUnit || !residentName.trim()) return;
    
    setActionLoading(true);
    setError("");
    setSuccessMsg("");
    setActivationResult(null);

    const hasActiveOwner = !!activeOwner;

    try {
      const response = await api.post("/api/v1/residents", {
        unit_id: selectedUnit.id,
        name: residentName.trim(),
        phone: !hasActiveOwner ? phone.trim() : undefined,
        email: !hasActiveOwner ? email.trim() : undefined,
      });

      setActivationResult({
        name: response.data.resident.name,
        token: response.data.activation_token,
        expiresAt: new Date(response.data.expires_at).toLocaleString(),
      });

      setSuccessMsg("Resident provisioned successfully!");
      setResidentName("");
      setPhone("");
      setEmail("");
      // Refresh list
      await fetchUnits();
      await fetchResidents(selectedUnit.id);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to provision resident");
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Revoke resident
  const handleRevoke = async (residentId: string) => {
    const consentPrompt = activeOwner
      ? `Have you called the Owner (${activeOwner.name} at ${activeOwner.phone}) to obtain verbal permission for this revocation?`
      : "Are you sure you want to revoke access for this resident?";

    if (!selectedUnit || !window.confirm(`${consentPrompt}\n\nThis action is permanent.`)) return;
    
    setActionLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      await api.patch(`/api/v1/residents/${residentId}/revoke`);
      setSuccessMsg("Access key revoked successfully!");
      // Refresh list
      await fetchUnits();
      await fetchResidents(selectedUnit.id);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to revoke resident access");
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Start edit contact modal
  const handleStartEditContact = (res: ResidentRead) => {
    setEditingOwner(res);
    setEditPhone(res.phone || "");
    setEditEmail(res.email || "");
  };

  // Save edit contact
  const handleUpdateContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingOwner) return;

    setActionLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      await api.patch(`/api/v1/residents/${editingOwner.id}/contact`, {
        phone: editPhone.trim(),
        email: editEmail.trim(),
      });
      setSuccessMsg("Owner contact updated successfully!");
      setEditingOwner(null);
      // Refresh list
      if (selectedUnit) {
        await fetchResidents(selectedUnit.id);
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to update contact info");
      }
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <header style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "1rem 2rem",
        background: "#1e3a8a",
        color: "white",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
      }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Vista Authen — Registration Dashboard</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span>Role: <strong>{role}</strong></span>
          <button onClick={onLogout} style={{
            padding: "0.5rem 1rem",
            backgroundColor: "#dc2626",
            border: "none",
            borderRadius: 4,
            color: "white",
            fontWeight: 600,
            cursor: "pointer"
          }}>Logout</button>
        </div>
      </header>

      {/* Main Grid */}
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "300px 1fr", padding: "1.5rem", gap: "1.5rem" }}>
        
        {/* Left Sidebar: Units */}
        <section style={{
          background: "white",
          borderRadius: 8,
          padding: "1rem",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          display: "flex",
          flexDirection: "column"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 style={{ margin: 0, fontSize: "1.2rem", color: "#374151" }}>Units</h2>
            <button onClick={fetchUnits} disabled={loadingUnits} style={{
              padding: "0.25rem 0.5rem",
              fontSize: "0.75rem",
              cursor: "pointer"
            }}>Refresh</button>
          </div>

          {loadingUnits ? (
            <p style={{ textAlign: "center", color: "#6b7280" }}>Loading units...</p>
          ) : (
            <div style={{ overflowY: "auto", flex: 1 }}>
              {units.map((unit) => {
                const isFull = unit.current_resident_count >= unit.max_residents;
                const isSelected = selectedUnit?.id === unit.id;
                
                return (
                  <div
                    key={unit.id}
                    onClick={() => {
                      setSelectedUnit(unit);
                      setActivationResult(null);
                      setSuccessMsg("");
                      setError("");
                    }}
                    style={{
                      padding: "0.75rem 1rem",
                      borderRadius: 6,
                      marginBottom: "0.5rem",
                      cursor: "pointer",
                      backgroundColor: isSelected ? "#eff6ff" : "transparent",
                      border: isSelected ? "1px solid #3b82f6" : "1px solid #e5e7eb",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <div>
                      <strong style={{ display: "block", color: "#1f2937" }}>Unit {unit.unit_number}</strong>
                      <span style={{ fontSize: "0.8rem", color: "#6b7280" }}>Limit: {unit.max_residents}</span>
                    </div>
                    <span style={{
                      padding: "0.25rem 0.5rem",
                      borderRadius: 12,
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      backgroundColor: isFull ? "#fef2f2" : "#f0fdf4",
                      color: isFull ? "#991b1b" : "#166534",
                      border: isFull ? "1px solid #fca5a5" : "1px solid #86efac"
                    }}>
                      {unit.current_resident_count}/{unit.max_residents}
                    </span>
                  </div>
                );
              })}
              {units.length === 0 && (
                <p style={{ textAlign: "center", color: "#9ca3af", marginTop: "2rem" }}>No units found</p>
              )}
            </div>
          )}
        </section>

        {/* Right Panel: Residents & Actions */}
        <section style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Messages */}
          {error && (
            <div style={{
              padding: "1rem",
              backgroundColor: "#fef2f2",
              color: "#991b1b",
              border: "1px solid #fca5a5",
              borderRadius: 6
            }}>{error}</div>
          )}
          {successMsg && !activationResult && (
            <div style={{
              padding: "1rem",
              backgroundColor: "#f0fdf4",
              color: "#166534",
              border: "1px solid #86efac",
              borderRadius: 6
            }}>{successMsg}</div>
          )}

          {selectedUnit ? (
            <>
              {/* Unit Header & Owner Callout */}
              <div style={{
                background: "white",
                borderRadius: 8,
                padding: "1.5rem",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)"
              }}>
                <h2 style={{ margin: "0 0 1rem 0", color: "#1e3a8a" }}>Unit {selectedUnit.unit_number} Details</h2>
                
                {/* Active Owner display */}
                {activeOwner ? (
                  <div style={{
                    padding: "1rem",
                    background: "#eff6ff",
                    border: "1px solid #bfdbfe",
                    borderRadius: 6,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                  }}>
                    <div>
                      <span style={{ fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, color: "#1e40af", display: "block", marginBottom: "0.25rem" }}>
                        🔑 Designated Apartment Owner (Resident #1)
                      </span>
                      <strong style={{ fontSize: "1.1rem", color: "#1e3a8a" }}>{activeOwner.name}</strong>
                      <div style={{ display: "flex", gap: "1.5rem", marginTop: "0.25rem", fontSize: "0.85rem", color: "#4b5563" }}>
                        <span>📞 Phone: <strong>{activeOwner.phone}</strong></span>
                        <span>✉️ Email: <strong>{activeOwner.email}</strong></span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleStartEditContact(activeOwner)}
                      style={{
                        padding: "0.4rem 0.8rem",
                        backgroundColor: "#3b82f6",
                        color: "white",
                        border: "none",
                        borderRadius: 4,
                        fontWeight: 600,
                        cursor: "pointer",
                        fontSize: "0.85rem"
                      }}
                    >
                      Edit Contact
                    </button>
                  </div>
                ) : (
                  <div style={{
                    padding: "1rem",
                    background: "#f9fafb",
                    border: "1px dashed #d1d5db",
                    borderRadius: 6,
                    color: "#6b7280",
                    fontSize: "0.875rem"
                  }}>
                    ℹ️ No owner designated. The first resident added to this unit will be set as Owner and must provide a telephone number and email.
                  </div>
                )}
              </div>

              {/* Staff Verbal Consent Prompts */}
              {activeOwner && (
                <div style={{
                  padding: "0.75rem 1rem",
                  background: "#fffbeb",
                  border: "1px solid #fde68a",
                  borderRadius: 6,
                  color: "#92400e",
                  fontSize: "0.85rem",
                  fontWeight: 500,
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem"
                }}>
                  📞 <span><strong>Permission Checklist:</strong> Resident Admin must call Owner <strong>{activeOwner.name}</strong> at <strong>{activeOwner.phone}</strong> to verify permission before adding, editing, or revoking other unit keys.</span>
                </div>
              )}

              {/* Activation Token Banner (Highly Visible) */}
              {activationResult && (
                <div style={{
                  background: "#fffbeb",
                  border: "2px solid #f59e0b",
                  borderRadius: 8,
                  padding: "1.5rem",
                  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
                }}>
                  <h3 style={{ margin: "0 0 0.75rem 0", color: "#b45309", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    ⚠️ Activation Token Generated
                  </h3>
                  <p style={{ margin: "0 0 1rem 0", color: "#78350f" }}>
                    Copy this token and hand it to <strong>{activationResult.name}</strong>. They will need it to activate their device at <code>{import.meta.env.VITE_RESIDENT_PORTAL_URL || "https://rbauth.example.com/"}</code>.
                  </p>
                  
                  <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
                    <input
                      type="text"
                      readOnly
                      value={activationResult.token}
                      style={{
                        flex: 1,
                        padding: "0.75rem",
                        fontFamily: "monospace",
                        fontSize: "1rem",
                        borderRadius: 4,
                        border: "1px solid #d1d5db",
                        backgroundColor: "#f9fafb"
                      }}
                    />
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(activationResult.token);
                        alert("Token copied to clipboard!");
                      }}
                      style={{
                        padding: "0.75rem 1.5rem",
                        backgroundColor: "#f59e0b",
                        border: "none",
                        borderRadius: 4,
                        color: "white",
                        fontWeight: 600,
                        cursor: "pointer"
                      }}
                    >
                      Copy Token
                    </button>
                  </div>
                  <span style={{ fontSize: "0.8rem", color: "#b45309" }}>
                    Expires at: <strong>{activationResult.expiresAt}</strong> (one-time use only).
                  </span>
                </div>
              )}

              {/* Residents List */}
              <div style={{
                background: "white",
                borderRadius: 8,
                padding: "1.5rem",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                flex: 1
              }}>
                <h3 style={{ margin: "0 0 1rem 0", color: "#374151" }}>Residents</h3>
                
                {loadingResidents ? (
                  <p style={{ textAlign: "center", color: "#6b7280" }}>Loading unit residents...</p>
                ) : (
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left", color: "#4b5563" }}>
                        <th style={{ padding: "0.75rem 0.5rem" }}>Name</th>
                        <th style={{ padding: "0.75rem 0.5rem" }}>Role</th>
                        <th style={{ padding: "0.75rem 0.5rem" }}>Status</th>
                        <th style={{ padding: "0.75rem 0.5rem" }}>Key Registered</th>
                        <th style={{ padding: "0.75rem 0.5rem" }}>Created At</th>
                        <th style={{ padding: "0.75rem 0.5rem", textAlign: "right" }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {residents.map((res) => (
                        <tr key={res.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                          <td style={{ padding: "0.75rem 0.5rem", fontWeight: 500, color: "#1f2937" }}>{res.name}</td>
                          <td style={{ padding: "0.75rem 0.5rem", color: "#4b5563" }}>
                            {res.is_owner ? (
                              <span style={{ color: "#2563eb", fontWeight: 600 }}>Owner (Primary)</span>
                            ) : (
                              <span style={{ color: "#6b7280" }}>Resident</span>
                            )}
                          </td>
                          <td style={{ padding: "0.75rem 0.5rem" }}>
                            <span style={{
                              padding: "0.25rem 0.5rem",
                              borderRadius: 4,
                              fontSize: "0.75rem",
                              fontWeight: 600,
                              textTransform: "uppercase",
                              backgroundColor: res.status === "active" ? "#d1fae5" : res.status === "pending" ? "#fef3c7" : "#fee2e2",
                              color: res.status === "active" ? "#065f46" : res.status === "pending" ? "#92400e" : "#991b1b"
                            }}>
                              {res.status}
                            </span>
                          </td>
                          <td style={{ padding: "0.75rem 0.5rem", color: "#4b5563" }}>
                            {res.has_public_key ? "🔒 Yes (Asymmetric)" : "❌ No"}
                          </td>
                          <td style={{ padding: "0.75rem 0.5rem", color: "#6b7280", fontSize: "0.85rem" }}>
                            {new Date(res.created_at).toLocaleString()}
                          </td>
                          <td style={{ padding: "0.75rem 0.5rem", textAlign: "right" }}>
                            {res.status !== "revoked" && (
                              <button
                                onClick={() => handleRevoke(res.id)}
                                disabled={actionLoading}
                                style={{
                                  padding: "0.4rem 0.75rem",
                                  backgroundColor: "#fee2e2",
                                  color: "#991b1b",
                                  border: "1px solid #fca5a5",
                                  borderRadius: 4,
                                  fontWeight: 500,
                                  cursor: actionLoading ? "not-allowed" : "pointer"
                                }}
                              >
                                Revoke
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                      {residents.length === 0 && !loadingResidents && (
                        <tr>
                          <td colSpan={6} style={{ padding: "2rem", textAlign: "center", color: "#9ca3af" }}>
                            No residents provisioned in this unit.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Provision Form */}
              <div style={{
                background: "white",
                borderRadius: 8,
                padding: "1.5rem",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)"
              }}>
                <h3 style={{ margin: "0 0 1rem 0", color: "#374151" }}>Provision New Resident</h3>
                
                {selectedUnit.current_resident_count >= selectedUnit.max_residents ? (
                  <div style={{
                    padding: "1rem",
                    backgroundColor: "#fff3cd",
                    color: "#856404",
                    border: "1px solid #ffeeba",
                    borderRadius: 6,
                    fontSize: "0.9rem"
                  }}>
                    ⚠️ <strong>Unit Capacity Reached:</strong> Cannot provision more residents. You must first increase the unit capacity or revoke existing residents.
                  </div>
                ) : (
                  <form onSubmit={handleProvision}>
                    {activeOwner && (
                      <div style={{
                        padding: "0.5rem 0.75rem",
                        background: "#fffbeb",
                        border: "1px solid #fde68a",
                        borderRadius: 4,
                        color: "#92400e",
                        fontSize: "0.8rem",
                        marginBottom: "1rem",
                        fontWeight: 500
                      }}>
                        📝 Notice: I confirm that I have called owner <strong>{activeOwner.name}</strong> and received permission to add this new resident.
                      </div>
                    )}

                    <div style={{ display: "flex", gap: "1rem", alignItems: "flex-end" }}>
                      <div style={{ flex: 1 }}>
                        <label htmlFor="res-name" style={{ display: "block", marginBottom: "0.5rem", fontSize: "0.875rem", color: "#4b5563", fontWeight: 500 }}>
                          Resident Name
                        </label>
                        <input
                          id="res-name"
                          type="text"
                          required
                          value={residentName}
                          onChange={(e) => setResidentName(e.target.value)}
                          placeholder="Enter resident's full name"
                          style={{
                            width: "100%",
                            padding: "0.6rem",
                            borderRadius: 4,
                            border: "1px solid #d1d5db",
                            boxSizing: "border-box"
                          }}
                        />
                      </div>
                      
                      {/* Only render provision action button here if regular resident (phone/email inputs NOT needed) */}
                      {activeOwner && (
                        <button
                          type="submit"
                          disabled={!residentName.trim() || actionLoading}
                          style={{
                            padding: "0.6rem 1.5rem",
                            backgroundColor: "#2563eb",
                            color: "white",
                            border: "none",
                            borderRadius: 4,
                            fontWeight: 600,
                            cursor: residentName.trim() && !actionLoading ? "pointer" : "not-allowed",
                            opacity: residentName.trim() && !actionLoading ? 1 : 0.7
                          }}
                        >
                          {actionLoading ? "Provisioning..." : "Provision Resident"}
                        </button>
                      )}
                    </div>

                    {/* Render contact inputs if unit has no owner (this first resident will be Owner) */}
                    {!activeOwner && (
                      <>
                        <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
                          <div style={{ flex: 1 }}>
                            <label htmlFor="res-phone" style={{ display: "block", marginBottom: "0.5rem", fontSize: "0.875rem", color: "#4b5563", fontWeight: 500 }}>
                              Telephone Number (Owner Required)
                            </label>
                            <input
                              id="res-phone"
                              type="tel"
                              required
                              value={phone}
                              onChange={(e) => setPhone(e.target.value)}
                              placeholder="e.g. +1234567890"
                              style={{
                                width: "100%",
                                padding: "0.6rem",
                                borderRadius: 4,
                                border: "1px solid #d1d5db",
                                boxSizing: "border-box"
                              }}
                            />
                          </div>
                          <div style={{ flex: 1 }}>
                            <label htmlFor="res-email" style={{ display: "block", marginBottom: "0.5rem", fontSize: "0.875rem", color: "#4b5563", fontWeight: 500 }}>
                              Email Address (Owner Required)
                            </label>
                            <input
                              id="res-email"
                              type="email"
                              required
                              value={email}
                              onChange={(e) => setEmail(e.target.value)}
                              placeholder="e.g. owner@example.com"
                              style={{
                                width: "100%",
                                padding: "0.6rem",
                                borderRadius: 4,
                                border: "1px solid #d1d5db",
                                boxSizing: "border-box"
                              }}
                            />
                          </div>
                        </div>
                        <button
                          type="submit"
                          disabled={!residentName.trim() || !phone.trim() || !email.trim() || actionLoading}
                          style={{
                            marginTop: "1.2rem",
                            width: "100%",
                            padding: "0.7rem",
                            backgroundColor: "#059669",
                            color: "white",
                            border: "none",
                            borderRadius: 4,
                            fontWeight: 600,
                            cursor: residentName.trim() && phone.trim() && email.trim() && !actionLoading ? "pointer" : "not-allowed",
                            opacity: residentName.trim() && phone.trim() && email.trim() && !actionLoading ? 1 : 0.7
                          }}
                        >
                          {actionLoading ? "Provisioning..." : "Provision Owner & Generate Token"}
                        </button>
                      </>
                    )}
                  </form>
                )}
              </div>
            </>
          ) : (
            <div style={{
              flex: 1,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              background: "white",
              borderRadius: 8,
              border: "1px dashed #d1d5db",
              color: "#6b7280"
            }}>
              <h3>Select a Unit from the sidebar to manage residents</h3>
            </div>
          )}
        </section>

      </div>

      {/* Edit Contact Modal */}
      {editingOwner && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 1000
        }}>
          <div style={{
            background: "white",
            padding: "2rem",
            borderRadius: 8,
            width: "100%",
            maxWidth: "400px",
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
          }}>
            <h3 style={{ margin: "0 0 1.2rem 0", color: "#1e3a8a", borderBottom: "1px solid #e5e7eb", paddingBottom: "0.5rem" }}>
              Edit Owner Contact Details
            </h3>
            <form onSubmit={handleUpdateContact}>
              <div style={{ marginBottom: "1rem" }}>
                <label htmlFor="edit-phone" style={{ display: "block", marginBottom: "0.5rem", fontSize: "0.875rem", color: "#4b5563", fontWeight: 500 }}>
                  Telephone Number
                </label>
                <input
                  id="edit-phone"
                  type="tel"
                  required
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    borderRadius: 4,
                    border: "1px solid #d1d5db",
                    boxSizing: "border-box"
                  }}
                />
              </div>
              <div style={{ marginBottom: "1.5rem" }}>
                <label htmlFor="edit-email" style={{ display: "block", marginBottom: "0.5rem", fontSize: "0.875rem", color: "#4b5563", fontWeight: 500 }}>
                  Email Address
                </label>
                <input
                  id="edit-email"
                  type="email"
                  required
                  value={editEmail}
                  onChange={(e) => setEditEmail(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    borderRadius: 4,
                    border: "1px solid #d1d5db",
                    boxSizing: "border-box"
                  }}
                />
              </div>
              
              <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={() => setEditingOwner(null)}
                  style={{
                    padding: "0.5rem 1rem",
                    border: "1px solid #d1d5db",
                    borderRadius: 4,
                    cursor: "pointer",
                    background: "white"
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!editPhone.trim() || !editEmail.trim() || actionLoading}
                  style={{
                    padding: "0.5rem 1rem",
                    backgroundColor: "#2563eb",
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    fontWeight: 600,
                    cursor: editPhone.trim() && editEmail.trim() && !actionLoading ? "pointer" : "not-allowed",
                    opacity: editPhone.trim() && editEmail.trim() && !actionLoading ? 1 : 0.7
                  }}
                >
                  {actionLoading ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

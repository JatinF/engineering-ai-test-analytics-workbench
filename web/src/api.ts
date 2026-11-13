export type Build = {
  build_id: string;
  version: string;
  created_at: string;
  change_note: string;
};

export type Investigation = {
  investigation_id: string;
  build_id: string;
  failure_code: string;
  classification: string;
  cause: string;
  citations: string[];
  notice: string;
  status: string;
  steps: { name: string; detail: string }[];
  wall_seconds: number;
};

export type CompareRow = {
  code: string;
  left_rate: number | null;
  right_rate: number | null;
  left_failures: number;
  right_failures: number;
};

export type Dashboard = {
  notice: string;
  pass_rates: { build_id: string; runs: number; passes: number; pass_rate: number }[];
  dq_failures: number;
  dq_by_reason: { reason: string; n: number }[];
  correction_rate: number;
  reviews: number;
  corrections: number;
  device_calls: number;
  mean_temperature_c: { build_id: string; mean_temperature_c: number | null }[];
  usage: { distinct_actors: string[]; investigate_events: number; repeated_subjects: number };
};

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(body.error ?? body.message ?? `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function loadBuilds(token: string): Promise<{ builds: Build[] }> {
  return request("/api/v1/builds", token);
}

export function startInvestigation(
  token: string,
  buildId: string,
  failureCode: string,
): Promise<Investigation> {
  return request("/api/v1/investigations", token, {
    method: "POST",
    body: JSON.stringify({ build_id: buildId, failure_code: failureCode }),
  });
}

export function loadInvestigations(token: string): Promise<{ investigations: Investigation[] }> {
  return request("/api/v1/investigations", token);
}

export function compareBuilds(
  token: string,
  left: string,
  right: string,
): Promise<{ rows: CompareRow[] }> {
  const query = new URLSearchParams({ left, right });
  return request(`/api/v1/builds/compare?${query.toString()}`, token);
}

export function submitReview(
  token: string,
  investigationId: string,
  action: "approve" | "correct",
  correctedCause: string,
): Promise<Investigation> {
  return request(`/api/v1/investigations/${investigationId}/review`, token, {
    method: "POST",
    body: JSON.stringify({ action, corrected_cause: correctedCause, note: "workbench review" }),
  });
}

export function loadDashboard(token: string): Promise<Dashboard> {
  return request("/api/v1/dashboard", token);
}

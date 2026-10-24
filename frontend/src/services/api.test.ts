import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/services/api";

function mockFetch(status: number, body: unknown, ok = status >= 200 && status < 300) {
  const fn = vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: "Status Text",
    json: async () => {
      if (body === undefined) throw new Error("not json");
      return body;
    },
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("token storage", () => {
  it("round-trips and clears", () => {
    expect(api.getToken()).toBeNull();
    api.setToken("abc");
    expect(api.getToken()).toBe("abc");
    api.clearToken();
    expect(api.getToken()).toBeNull();
  });
});

describe("request plumbing", () => {
  it("sends the bearer token when logged in and none when not", async () => {
    const fetchMock = mockFetch(200, { status: "ok" });
    await api.getHealth();
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();

    api.setToken("tok123");
    await api.getHealth();
    expect(fetchMock.mock.calls[1][0]).toBe("/api/health");
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe("Bearer tok123");
  });

  it("login posts credentials as JSON", async () => {
    const fetchMock = mockFetch(200, { access_token: "t", role: "ADMIN" });
    await api.login("admin", "admin123");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/login");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ username: "admin", password: "admin123" });
  });

  it("surfaces the server's detail message as an ApiError", async () => {
    mockFetch(403, { detail: "Role 'VIEWER' is not permitted to perform this action." });
    await expect(api.stopSimulator()).rejects.toMatchObject({
      name: "Error",
      status: 403,
      message: "Role 'VIEWER' is not permitted to perform this action.",
    });
  });

  it("falls back to statusText when the error body isn't JSON", async () => {
    mockFetch(502, undefined);
    const err = await api.getHealth().catch((e) => e);
    expect(err).toBeInstanceOf(api.ApiError);
    expect(err.status).toBe(502);
    expect(err.message).toBe("Status Text");
  });

  it("a 401 clears the stored token so the user is sent back to login", async () => {
    api.setToken("expired");
    mockFetch(401, { detail: "Could not validate credentials" });
    await expect(api.getMe()).rejects.toMatchObject({ status: 401 });
    expect(api.getToken()).toBeNull();
  });

  it("other errors keep the token", async () => {
    api.setToken("keep");
    mockFetch(500, { detail: "boom" });
    await expect(api.getMe()).rejects.toMatchObject({ status: 500 });
    expect(api.getToken()).toBe("keep");
  });
});

describe("query-string building", () => {
  it("omits empty params", async () => {
    const f = mockFetch(200, []);
    await api.getEvents();
    expect(f.mock.calls[0][0]).toBe("/api/events");
  });

  it("includes only the params given", async () => {
    const f = mockFetch(200, []);
    await api.getEvents({ limit: 20, source: "dns" });
    expect(f.mock.calls[0][0]).toBe("/api/events?limit=20&source=dns");
    await api.getIncidents({ status: "open", severity: "high" });
    expect(f.mock.calls[1][0]).toBe("/api/incidents?status=open&severity=high");
    await api.getAuditLogs({ resource_type: "incident", resource_id: "INC-1001" });
    expect(f.mock.calls[2][0]).toBe("/api/audit?resource_type=incident&resource_id=INC-1001");
    await api.getMlPredictions({ anomalous_only: true });
    expect(f.mock.calls[3][0]).toBe("/api/ml/predictions?anomalous_only=true");
  });

  it("uses the backend's status_filter name for response actions", async () => {
    const f = mockFetch(200, []);
    await api.getAllResponseActions("recommended");
    expect(f.mock.calls[0][0]).toBe("/api/response?status_filter=recommended");
    await api.getAllResponseActions();
    expect(f.mock.calls[1][0]).toBe("/api/response");
  });
});

describe("mutating calls hit the right endpoints", () => {
  it.each([
    ["approve", () => api.approveResponseAction("RESP-000001"), "/api/response/RESP-000001/approve"],
    ["reject", () => api.rejectResponseAction("RESP-000001"), "/api/response/RESP-000001/reject"],
    ["investigate", () => api.investigateIncident("INC-1001"), "/api/incidents/INC-1001/investigate"],
    ["stop", () => api.stopSimulator(), "/api/simulator/stop"],
  ])("%s", async (_n, call, url) => {
    const f = mockFetch(200, {});
    await call();
    expect(f.mock.calls[0][0]).toBe(url);
    expect(f.mock.calls[0][1].method).toBe("POST");
  });

  it("startSimulator and updateRule send their bodies", async () => {
    const f = mockFetch(200, {});
    await api.startSimulator("multi_stage");
    expect(JSON.parse(f.mock.calls[0][1].body)).toEqual({ scenario: "multi_stage" });
    await api.updateRule("brute_force", { enabled: false, config: { failed_threshold: 9 } });
    expect(JSON.parse(f.mock.calls[1][1].body)).toEqual({
      rule_key: "brute_force",
      enabled: false,
      config: { failed_threshold: 9 },
    });
  });

  it("trainMlModel defaults match the backend defaults", async () => {
    const f = mockFetch(200, {});
    await api.trainMlModel();
    expect(JSON.parse(f.mock.calls[0][1].body)).toEqual({ contamination: 0.05, window_minutes: 5 });
  });

  it("preprocessDataset sends null (not empty string) for no label column", async () => {
    const f = mockFetch(200, {});
    await api.preprocessDataset("d.csv", "");
    expect(JSON.parse(f.mock.calls[0][1].body)).toEqual({ raw_filename: "d.csv", label_column: null });
  });
});

describe("uploadDataset", () => {
  it("sends multipart without forcing a JSON content type, with auth", async () => {
    api.setToken("t");
    const f = mockFetch(201, { filename: "a.csv", size_bytes: 3, modified_at: "now" });
    const file = new File(["a,b"], "a.csv", { type: "text/csv" });
    await api.uploadDataset(file);
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("/api/dataset/upload");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
    expect(init.headers["Content-Type"]).toBeUndefined(); // browser must set the multipart boundary
    expect(init.headers.Authorization).toBe("Bearer t");
  });

  it("raises the server's message on rejection", async () => {
    mockFetch(400, { detail: "Unsupported file type '.exe'. Only .csv and .parquet are supported." });
    await expect(api.uploadDataset(new File(["x"], "x.exe"))).rejects.toMatchObject({
      status: 400,
      message: expect.stringContaining("Only .csv and .parquet"),
    });
  });
});

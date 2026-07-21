import { describe, expect, it } from "vitest";

import { buildBrowserClipperBookmarklet } from "./vnext-workspace-model";

describe("browser clipper bookmarklet", () => {
  const capability = "alice_clip_one_time_capability";
  const bookmarklet = buildBrowserClipperBookmarklet({
    endpoint: "http://127.0.0.1:8000/v0/vnext/connectors/browser-clipper/capture",
    userId: "user-1",
    capability,
    origin: "https://example.com",
    domain: "professional",
    sensitivity: "private",
  });

  it("uses only an origin-bound one-time capability in visited-page code", () => {
    expect(bookmarklet.startsWith("javascript:")).toBe(true);
    expect(bookmarklet).toContain(`const capture_capability=${JSON.stringify(capability)}`);
    expect(bookmarklet).toContain('const expected_origin="https://example.com"');
    expect(bookmarklet).toContain("location.origin!==expected_origin");
    expect(bookmarklet).not.toContain("capture_token");
    expect(bookmarklet).not.toContain("Authorization");
    expect(bookmarklet).not.toContain("agent_api_key");
  });

  it("uses a CORS-safelisted opaque transport without claiming the write succeeded", () => {
    expect(bookmarklet).toContain('await fetch(endpoint,{method:"POST",mode:"no-cors",body:JSON.stringify(body)})');
    expect(bookmarklet).not.toContain("headers:");
    expect(bookmarklet).not.toContain("Content-Type");
    expect(bookmarklet).not.toContain(".ok");
    expect(bookmarklet).not.toContain(".status");
    expect(bookmarklet).toContain("Alice clip request submitted. Verify it in the Alice Inbox.");
    expect(bookmarklet).toContain("Alice clip request failed before submission.");
  });

  it("does not prompt the hostile page context for endpoint, identity, or reusable credentials", () => {
    expect(bookmarklet).not.toContain("Alice API endpoint");
    expect(bookmarklet).not.toContain("Alice user id");
    expect(bookmarklet).not.toContain("clipper token");
    expect(bookmarklet.match(/prompt\(/g)).toHaveLength(1);
    expect(bookmarklet).toContain('prompt("Optional note","")');
  });

  it("serializes trusted inputs rather than interpolating executable text", () => {
    const injected = buildBrowserClipperBookmarklet({
      endpoint: 'http://127.0.0.1:8000/clip?value=";alert(1);//',
      userId: 'user-";alert(2);//',
      capability: 'alice_clip_";alert(3);//',
      origin: "https://example.com",
      domain: "professional",
      sensitivity: "private",
    });

    expect(injected).toContain(JSON.stringify('http://127.0.0.1:8000/clip?value=";alert(1);//'));
    expect(injected).toContain(JSON.stringify('user-";alert(2);//'));
    expect(injected).toContain(JSON.stringify('alice_clip_";alert(3);//'));
  });
});

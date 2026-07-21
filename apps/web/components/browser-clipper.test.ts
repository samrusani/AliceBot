import { describe, expect, it } from "vitest";

import { buildBrowserClipperBookmarklet } from "./vnext-workspace-model";

describe("browser clipper bookmarklet", () => {
  const configEncoding = /^(?:[A-Za-z0-9._~-]|%25[0-9A-F]{2})+$/;
  const capability = "alice_clip_one_time_capability";
  const input = {
    endpoint: "http://127.0.0.1:8000/v0/vnext/connectors/browser-clipper/capture",
    userId: "user-1",
    capability,
    origin: "https://example.com",
    domain: "professional" as const,
    sensitivity: "private" as const,
  };
  const bookmarklet = buildBrowserClipperBookmarklet({
    ...input,
  });

  function decodedConfig(value: string) {
    const match = value.match(/decodeURIComponent\("([^"\\]+)"\)/);
    expect(match).not.toBeNull();
    const encoded = match?.[1] ?? "";
    expect(encoded).toMatch(configEncoding);
    const executableEncoding = encoded.replaceAll("%25", "%");
    return JSON.parse(decodeURIComponent(executableEncoding));
  }

  it("uses only an origin-bound one-time capability in visited-page code", () => {
    const protocol = new URL(bookmarklet).protocol;
    expect(protocol).toBe("javascript:");
    expect(protocol).not.toBe("data:");
    expect(protocol).not.toBe("vbscript:");
    expect(decodedConfig(bookmarklet)).toEqual({
      endpoint: input.endpoint,
      user_id: input.userId,
      capture_capability: input.capability,
      expected_origin: input.origin,
      domain: input.domain,
      sensitivity: input.sensitivity,
    });
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

  it("round-trips adversarial Unicode inputs through a strict non-executable encoding", () => {
    const adversarial = `double" single' slash\\ 100% / %41 close</script><script>alert(1)</script>\u2028\u2029 café 雪 😀`;
    const adversarialInput = {
      endpoint: `https://example.com/capture/${adversarial}`,
      userId: `user-${adversarial}`,
      capability: `alice_clip_${adversarial}`,
      origin: `https://example.com/${adversarial}`,
      domain: "professional" as const,
      sensitivity: "private" as const,
    };
    const injected = buildBrowserClipperBookmarklet({
      ...adversarialInput,
    });

    expect(decodedConfig(injected)).toEqual({
      endpoint: adversarialInput.endpoint,
      user_id: adversarialInput.userId,
      capture_capability: adversarialInput.capability,
      expected_origin: adversarialInput.origin,
      domain: adversarialInput.domain,
      sensitivity: adversarialInput.sensitivity,
    });
    expect(injected).not.toContain("</script>");
    expect(injected).not.toContain("\\");
    expect(injected).not.toContain("\u2028");
    expect(injected).not.toContain("\u2029");
  });
});

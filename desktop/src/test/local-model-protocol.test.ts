import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import test from "node:test";
import { createLocalModelServer } from "../local-model-protocol";

const token = "t".repeat(43);

test("local model protocol rejects missing bearer tokens and returns JSON completions", async () => {
  let capturedSchema = false;
  const server = createLocalModelServer({
    token,
    modelName: "Qwen3-0.6B-Q8_0",
    generator: async (request) => {
      capturedSchema = Boolean(request.responseSchema);
      assert.equal(request.messages[0].role, "system");
      return {
        text: '{"items":[]}',
        promptTokens: 12,
        completionTokens: 4,
      };
    },
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address() as AddressInfo;
  const base = `http://127.0.0.1:${address.port}`;
  try {
    const denied = await fetch(`${base}/health`);
    assert.equal(denied.status, 401);

    const response = await fetch(`${base}/v1/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "Qwen3-0.6B-Q8_0",
        messages: [
          { role: "system", content: "Return JSON" },
          { role: "user", content: "Plan one step" },
        ],
        max_tokens: 64,
        temperature: 0,
        response_format: {
          type: "json_schema",
          json_schema: {
            name: "result",
            schema: {
              type: "object",
              properties: { items: { type: "array" } },
            },
          },
        },
      }),
    });
    assert.equal(response.status, 200);
    const payload = (await response.json()) as Record<string, any>;
    assert.equal(payload.choices[0].message.content, '{"items":[]}');
    assert.equal(payload.usage.total_tokens, 16);
    assert.equal(capturedSchema, true);
  } finally {
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
});

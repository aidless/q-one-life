export interface SupportEvent {
  at: string;
  kind: string;
  message: string;
}

export interface SupportPackageInput {
  application: {
    version: string;
    packaged: boolean;
    electron: string;
    chrome: string;
    node: string;
  };
  system: {
    platform: string;
    release: string;
    arch: string;
    locale: string;
  };
  runtime: Record<string, unknown>;
  events: readonly SupportEvent[];
}

export function redactSupportText(value: string): string {
  return value
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]")
    .replace(
      /(authorization|x-qone-capability|x-qone-control|api[_-]?key|token)\s*[:=]\s*(?:Bearer\s+)?\S+/gi,
      "$1=[REDACTED]",
    )
    .replace(
      /(cloud_key|capability|control|local_model_token)\s*["']?\s*[:=]\s*["']?[^,\s"']+/gi,
      "$1=[REDACTED]",
    )
    .replace(/\b[A-Za-z]:\\[^\s,;)"']+/g, "[PATH]")
    .replace(
      /(^|[\s("'])\/(?:home|Users|tmp|var|private|mnt|opt)\/[^\s,;)"']+/g,
      "$1[PATH]",
    )
    .replace(/\b(?:sk|qone|key)[-_][A-Za-z0-9_-]{16,}\b/g, "[REDACTED]");
}

function redactValue(value: unknown): unknown {
  if (typeof value === "string") return redactSupportText(value);
  if (Array.isArray(value)) return value.map(redactValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [
        key,
        /(?:secret|token|capability|control|key|path|directory)/i.test(key)
          ? "[OMITTED]"
          : redactValue(item),
      ]),
    );
  }
  return value;
}

export function buildSupportPackage(input: SupportPackageInput): Record<string, unknown> {
  return {
    schema: "q-one-support-v1",
    created_at: new Date().toISOString(),
    application: input.application,
    system: input.system,
    runtime: redactValue(input.runtime),
    events: input.events.slice(-100).map((event) => ({
      at: event.at,
      kind: redactSupportText(event.kind),
      message: redactSupportText(event.message),
    })),
    privacy: {
      includes_personal_records: false,
      includes_working_database: false,
      includes_absolute_paths: false,
      includes_secrets: false,
    },
  };
}

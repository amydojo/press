import { z } from "zod";

const httpUrl = z
  .url()
  .refine((value) => value.startsWith("http://") || value.startsWith("https://"), {
    message: "must use http or https",
  });

const serverEnvironmentSchema = z.object({
  API_BASE_URL: httpUrl.default("http://localhost:8000"),
  PRESS_ENV: z.enum(["development", "test", "preview", "production"]).default("development"),
  PRESS_VERSION: z.string().min(1).default("0.1.0"),
});

const publicEnvironmentSchema = z.object({
  NEXT_PUBLIC_APP_URL: httpUrl.default("http://localhost:3000"),
});

export type ServerEnvironment = z.infer<typeof serverEnvironmentSchema>;
export type PublicEnvironment = z.infer<typeof publicEnvironmentSchema>;

export function parseServerEnvironment(input: Record<string, string | undefined>): ServerEnvironment {
  return serverEnvironmentSchema.parse(input);
}

export function getServerEnvironment(): ServerEnvironment {
  return parseServerEnvironment({
    API_BASE_URL: process.env.API_BASE_URL,
    PRESS_ENV: process.env.PRESS_ENV,
    PRESS_VERSION: process.env.PRESS_VERSION,
  });
}

export function parsePublicEnvironment(input: Record<string, string | undefined>): PublicEnvironment {
  return publicEnvironmentSchema.parse(input);
}

export function getPublicEnvironment(): PublicEnvironment {
  return parsePublicEnvironment({
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
  });
}

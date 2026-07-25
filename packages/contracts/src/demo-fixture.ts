import { z } from "zod";

export const demoSourceFixtureSchema = z.object({
  fixtureVersion: z.literal("1.0"),
  sourceType: z.literal("fixture"),
  domain: z.literal("demo.press.local"),
  title: z.string().min(1),
  fragment: z.string().min(1),
  exampleNote: z.string().min(1).max(120),
  localHtmlPath: z.string().min(1),
  previewPath: z.string().min(1),
});

export type DemoSourceFixture = z.infer<typeof demoSourceFixtureSchema>;

export function parseDemoSourceFixture(input: unknown): DemoSourceFixture {
  return demoSourceFixtureSchema.parse(input);
}

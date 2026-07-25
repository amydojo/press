import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";

const root = process.argv[2];
if (!root) throw new Error("Usage: node scripts/check-client-secrets.mjs <client-static-directory>");

const forbidden = [
  "B2_KEY_ID",
  "B2_APPLICATION_KEY",
  "B2_BUCKET_NAME",
  "B2_ENDPOINT",
  "GENBLAZE_PROVIDER_API_KEY",
  "press-ci-b2-secret-sentinel",
  "press-ci-provider-secret-sentinel",
];

async function filesUnder(directory) {
  const entries = await readdir(directory);
  const files = [];
  for (const entry of entries) {
    const absolute = path.join(directory, entry);
    const metadata = await stat(absolute);
    if (metadata.isDirectory()) files.push(...(await filesUnder(absolute)));
    else files.push(absolute);
  }
  return files;
}

const files = await filesUnder(root);
const findings = [];
for (const file of files) {
  const content = await readFile(file, "utf8").catch(() => "");
  for (const token of forbidden) {
    if (content.includes(token)) findings.push(`${file}: ${token}`);
  }
}

if (findings.length > 0) {
  console.error("Server-only secret material was found in the client bundle:\n" + findings.join("\n"));
  process.exit(1);
}

console.log(`Client bundle inspected: ${files.length} files, no forbidden secret names or sentinels found.`);

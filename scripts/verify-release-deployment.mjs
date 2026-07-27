#!/usr/bin/env node

const appUrl = process.env.PRESS_RELEASE_WEB_URL;
const expectedSha = process.env.PRESS_RELEASE_COMMIT_SHA;

if (!appUrl || !expectedSha) {
  console.error("PRESS_RELEASE_WEB_URL and PRESS_RELEASE_COMMIT_SHA are required.");
  process.exit(2);
}

const normalized = appUrl.replace(/\/$/, "");
const routes = ["/", "/press/new"];

for (const route of routes) {
  const response = await fetch(`${normalized}${route}`, { redirect: "manual" });
  if (response.status < 200 || response.status >= 400) {
    console.error(`${route} returned ${response.status}.`);
    process.exit(1);
  }
}

const deploymentResponse = await fetch(`${normalized}/api/system/health`, { cache: "no-store" });
if (!deploymentResponse.ok) {
  console.error(`/api/system/health returned ${deploymentResponse.status}.`);
  process.exit(1);
}

const payload = await deploymentResponse.json();
const deployedSha = payload.commitSha ?? payload.commit ?? payload.gitSha;

if (!deployedSha) {
  console.error("The deployed health response does not expose a commit SHA. Add release identity before claiming exact-build verification.");
  process.exit(1);
}

if (!expectedSha.startsWith(deployedSha) && !deployedSha.startsWith(expectedSha)) {
  console.error(`Deployment commit mismatch. Expected ${expectedSha}, received ${deployedSha}.`);
  process.exit(1);
}

console.log(`Verified ${normalized} at commit ${deployedSha}.`);

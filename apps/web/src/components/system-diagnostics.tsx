"use client";

import { useEffect, useState } from "react";

import type { SystemDiagnostics as Diagnostics } from "@/lib/system-contract";
import { loadSystemDiagnostics } from "@/lib/system-client";

type State =
  | { kind: "loading" }
  | { kind: "loaded"; data: Diagnostics }
  | { kind: "malformed-client-response" };

export function SystemDiagnostics() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    void loadSystemDiagnostics()
      .then((data) => {
        if (active) setState({ kind: "loaded", data });
      })
      .catch(() => {
        if (active) setState({ kind: "malformed-client-response" });
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") {
    return (
      <section className="diagnostic-card" aria-live="polite" aria-busy="true">
        <p className="eyebrow">System diagnostics</p>
        <h1>Checking the foundation.</h1>
        <p>Web status: loading</p>
        <p>Generation API status: loading</p>
      </section>
    );
  }

  if (state.kind === "malformed-client-response") {
    return (
      <section className="diagnostic-card" aria-live="assertive">
        <p className="eyebrow">System diagnostics</p>
        <h1>Diagnostics response malformed.</h1>
        <p>The web application is running, but its internal diagnostics response failed validation.</p>
      </section>
    );
  }

  const { data } = state;
  if (data.apiStatus === "healthy") {
    return (
      <section className="diagnostic-card" aria-live="polite">
        <p className="eyebrow">System diagnostics</p>
        <h1>Foundation online.</h1>
        <dl>
          <div><dt>Web status</dt><dd>healthy</dd></div>
          <div><dt>Generation API status</dt><dd>healthy</dd></div>
          <div><dt>API version</dt><dd>{data.apiVersion}</dd></div>
          <div><dt>Environment</dt><dd>{data.environment}</dd></div>
          <div><dt>Contract version</dt><dd>{data.contractVersion}</dd></div>
          <div><dt>Request ID</dt><dd className="mono">{data.requestId}</dd></div>
        </dl>
      </section>
    );
  }

  if (data.apiStatus === "malformed") {
    return (
      <section className="diagnostic-card" aria-live="assertive">
        <p className="eyebrow">System diagnostics</p>
        <h1>Generation API response malformed.</h1>
        <p>The web application is healthy. The API answered, but the payload did not match the generated contract.</p>
      </section>
    );
  }

  return (
    <section className="diagnostic-card" aria-live="assertive">
      <p className="eyebrow">System diagnostics</p>
      <h1>Generation API unreachable.</h1>
      <p>The web application is healthy. No healthy API result is being faked.</p>
      <p className="mono">Reason: {data.reason}</p>
    </section>
  );
}

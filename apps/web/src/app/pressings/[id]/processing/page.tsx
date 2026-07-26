"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Recovery } from "@/components/recovery";
import { browserRepository, failPressing, processingPhases, type Pressing, type PressingStatus } from "@/lib/pressings";

const PHASE_MS = 3000;
const REDUCED_PHASE_MS = 500;

export default function ProcessingPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [pressing, setPressing] = useState<Pressing | null | undefined>(undefined);
  const [reduced, setReduced] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fixtureFailure = useRef(false);
  const failedOnce = useRef(false);

  useEffect(() => {
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    fixtureFailure.current = new URL(window.location.href).searchParams.get("fixtureFailure") === "1";
    setPressing(browserRepository().read(id));
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [id]);

  useEffect(() => {
    if (!pressing) return;
    if (pressing.status === "ready" || pressing.status === "kept") {
      router.replace(`/pressings/${id}`);
      return;
    }
    if (pressing.status === "failed" || pressing.status === "registered") return;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      try {
        if (fixtureFailure.current && !failedOnce.current) {
          failedOnce.current = true;
          const failed = failPressing(pressing);
          browserRepository().save(failed);
          setPressing(failed);
          return;
        }
        const index = processingPhases.findIndex((phase) => phase.status === pressing.status);
        const next = index === processingPhases.length - 1 ? "ready" : processingPhases[index + 1]?.status;
        if (!next) throw new Error("Unknown processing state");
        setPressing(browserRepository().advance(id, next as PressingStatus));
      } catch {
        try {
          const failed = failPressing(pressing);
          browserRepository().save(failed);
          setPressing(failed);
        } catch {
          setPressing(browserRepository().read(id));
        }
      }
    }, reduced ? REDUCED_PHASE_MS : PHASE_MS);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [id, pressing, reduced, router]);

  const phaseIndex = useMemo(() => processingPhases.findIndex((phase) => phase.status === pressing?.status), [pressing]);
  const phase = phaseIndex >= 0 ? processingPhases[phaseIndex] : null;

  if (pressing === undefined) return <main className="page-shell" aria-busy="true" />;
  if (!pressing) return <Recovery title="Pressing not found" message="This local pressing is missing or could not be reconstructed." />;
  if (pressing.status === "registered") return <Recovery title="Pressing has not begun" message="Confirm the registered source before manufacturing starts." />;
  if (pressing.status === "failed") {
    return (
      <main className="page-shell page-shell--top">
        <header className="site-header"><Link href="/" className="brand">PRESS</Link><Link href="/archive" className="quiet-link">Archive</Link></header>
        <section className="processing processing--failed">
          <p className="eyebrow">Manufacturing paused</p>
          <h1 className="display-small">The pressing did not seal.</h1>
          <p>The registered source is intact. Retry resumes this same record from a safe reading state.</p>
          <button className="button button--primary" type="button" onClick={() => setPressing(browserRepository().retry(id))}>Retry pressing</button>
        </section>
      </main>
    );
  }
  if (!phase) return <Recovery title="Wrong route for this pressing" message={`This pressing is currently ${pressing.status}.`} />;

  return (
    <main className="page-shell page-shell--top">
      <header className="site-header"><Link href="/" className="brand">PRESS</Link><span className="quiet-label">{pressing.number}</span></header>
      <section className="processing" aria-labelledby="processing-title">
        <div className={`press-machine press-machine--${pressing.status}`} aria-hidden="true">
          <div className="press-machine__rail" />
          <div className="press-machine__plate"><span>{phaseIndex + 1}</span></div>
          <div className="press-machine__bed"><span /></div>
        </div>
        <div className="processing-copy" aria-live="polite">
          <p className="eyebrow">Manufacturing · {phaseIndex + 1}/{processingPhases.length}</p>
          <h1 id="processing-title" className="display-small">{phase.label}</h1>
          <ol className="phase-list" aria-label="Pressing phases">
            {processingPhases.map((item, index) => <li key={item.status} aria-current={index === phaseIndex ? "step" : undefined} className={index <= phaseIndex ? "is-active" : ""}>{item.label}</li>)}
          </ol>
        </div>
      </section>
    </main>
  );
}

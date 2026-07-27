"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { PressingObject } from "@/components/pressing-object";
import { deletePressing, type PressingResponse } from "@/lib/pressings";

export function PressingDetail({ response }: { response: PressingResponse }) {
  const router = useRouter();
  const [back, setBack] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const pressing = response.pressing;
  const sourceUrl = pressing.source.canonicalUrl ?? pressing.source.submittedUrl;
  const capturedAt = pressing.source.capturedAt ?? pressing.createdAt;

  useEffect(() => {
    const frame = requestAnimationFrame(() => setRevealed(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  async function remove() {
    const domain = pressing.source.domain ?? pressing.anchors.submittedSourceIdentity;
    if (!window.confirm(`Delete ${pressing.serialNumber}?\n\nThis removes the source copy, generated attempts, and pressing from PRESS. The original page is not affected.\n\nSource: ${domain}`)) return;
    setDeleting(true);
    try {
      await deletePressing(pressing.id);
      router.push("/pressings");
      router.refresh();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "PRESS could not delete this pressing.");
      setDeleting(false);
    }
  }

  return (
    <div className={`detail-layout ${revealed ? "detail-layout--revealed" : ""}`}>
      <section className="detail-object" aria-labelledby="object-title">
        <div className="reveal-chamber" aria-hidden="true"><span /><span /></div>
        <h2 id="object-title" className="sr-only">Inspect pressing</h2>
        <PressingObject
          pressing={pressing}
          assetUrl={response.finalAssetAccess?.url}
          back={back}
          interactive
          revealed={revealed}
          onSideChange={setBack}
        />
        <div className="segmented-control" aria-label="Pressing side">
          <button type="button" aria-pressed={!back} onClick={() => setBack(false)}>View front</button>
          <button type="button" aria-pressed={back} onClick={() => setBack(true)}>View back</button>
        </div>
        <p className="inspection-hint">Move across the object to inspect its depth. Double click to flip.</p>
      </section>
      <section className="detail-copy">
        <p className="eyebrow">{pressing.serialNumber}</p>
        <h1>{pressing.source.title ?? pressing.source.domain ?? "Untitled source"}</h1>
        <blockquote>{pressing.anchors.selectedFragment}</blockquote>
        <p className="personal-note">{pressing.anchors.personalNote}</p>
        <dl>
          <div><dt>Source</dt><dd>{pressing.source.domain ?? pressing.anchors.submittedSourceIdentity}</dd></div>
          <div><dt>Captured</dt><dd>{capturedAt ? new Date(capturedAt).toLocaleString() : "Unknown"}</dd></div>
          <div><dt>Archetype</dt><dd>{pressing.final?.internalArchetype ?? pressing.understanding?.archetype ?? "pending"}</dd></div>
        </dl>
        <div className="detail-actions">
          {sourceUrl ? <a className="primary-button" href={sourceUrl} target="_blank" rel="noopener noreferrer">View source ↗</a> : null}
          <Link className="secondary-button" href="/press/new">Make another</Link>
          <button className="danger-button" type="button" onClick={remove} disabled={deleting}>{deleting ? "Deleting…" : "Delete pressing"}</button>
        </div>
        <details><summary>Generation details</summary><p>Provider and model provenance remain secondary to the object. Attempts: {pressing.attempts?.length ?? 0}.</p></details>
      </section>
    </div>
  );
}

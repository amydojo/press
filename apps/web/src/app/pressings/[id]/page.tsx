"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PressingArtifact } from "@/components/artifact";
import { Recovery } from "@/components/recovery";
import { browserRepository, type Pressing } from "@/lib/pressings";

export default function PressingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [pressing, setPressing] = useState<Pressing | null | undefined>(undefined);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => setPressing(browserRepository().read(id)), [id]);

  if (pressing === undefined) return <main className="page-shell" aria-busy="true" />;
  if (!pressing) return <Recovery title="Pressing not found" message="This local pressing is missing or could not be read." />;
  if (pressing.status !== "ready" && pressing.status !== "kept") {
    return <Recovery title="Artifact not ready" message={`This pressing is currently ${pressing.status}. PRESS will not reveal unfinished material.`} />;
  }

  function keep() {
    const kept = browserRepository().keep(id);
    setPressing(kept);
    setAnnouncement("Pressing kept.");
  }

  return (
    <main className="page-shell page-shell--reveal">
      <header className="site-header"><Link href="/" className="brand">PRESS</Link><Link href="/archive" className="quiet-link">Archive</Link></header>
      <section className="reveal" aria-labelledby="artifact-title">
        <div className="reveal-stage"><PressingArtifact pressing={pressing} /></div>
        <div className="reveal-copy">
          <p className="eyebrow">Artifact · {pressing.number}</p>
          <h1 id="artifact-title" className="display-small">{pressing.result?.title}</h1>
          <p className="archetype">{pressing.result?.archetype}</p>
          <p className="interpretation">{pressing.result?.interpretation}</p>
          <dl className="metadata-list">
            <div><dt>Source</dt><dd>Text</dd></div>
            <div><dt>Created</dt><dd><time dateTime={pressing.createdAt}>{new Date(pressing.createdAt).toLocaleDateString()}</time></dd></div>
          </dl>
          <div className="action-row">
            {pressing.status === "ready" ? <button className="button button--primary" type="button" onClick={keep}>Keep this pressing</button> : <Link className="button button--primary" href="/archive">View archive</Link>}
            <button className="text-button" type="button" aria-expanded={sourceOpen} onClick={() => setSourceOpen((open) => !open)}>View source</button>
            <Link className="text-button" href="/">Press again</Link>
          </div>
          <p className="confirmation" role="status" aria-live="polite">{announcement || (pressing.status === "kept" ? "Pressing kept." : "")}</p>
          {sourceOpen && <blockquote className="source-disclosure">{pressing.source.content}</blockquote>}
        </div>
      </section>
    </main>
  );
}

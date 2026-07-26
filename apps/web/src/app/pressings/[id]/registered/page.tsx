"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Recovery } from "@/components/recovery";
import { browserRepository, type Pressing } from "@/lib/pressings";

export default function RegisteredPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const firing = useRef(false);
  const [pressing, setPressing] = useState<Pressing | null | undefined>(undefined);

  useEffect(() => setPressing(browserRepository().read(id)), [id]);

  if (pressing === undefined) return <main className="page-shell" aria-busy="true" />;
  if (!pressing) return <Recovery title="Pressing not found" message="This local pressing is missing or could not be read." />;
  if (pressing.status !== "registered") return <Recovery title="Source is not awaiting registration" message={`This pressing is currently ${pressing.status}. Open its truthful destination instead.`} />;

  function begin() {
    if (firing.current) return;
    firing.current = true;
    try {
      browserRepository().advance(id, "reading");
      router.push(`/pressings/${id}/processing`);
    } catch {
      firing.current = false;
    }
  }

  function replace() {
    if (firing.current) return;
    firing.current = true;
    browserRepository().remove(id);
    router.replace("/");
  }

  return (
    <main className="page-shell page-shell--top">
      <header className="site-header"><Link href="/" className="brand">PRESS</Link><Link href="/archive" className="quiet-link">Archive</Link></header>
      <section className="registration" aria-labelledby="registration-title">
        <div className="registration-heading">
          <p className="eyebrow">Source registered</p>
          <h1 id="registration-title" className="display-small">Material received.</h1>
        </div>
        <article className="source-slip">
          <header><strong>{pressing.number}</strong><span>TEXT</span></header>
          <blockquote>{pressing.source.content}</blockquote>
          <footer><span>REGISTERED</span><time dateTime={pressing.source.registeredAt}>{new Date(pressing.source.registeredAt).toLocaleString()}</time></footer>
        </article>
        <div className="action-row">
          <button className="button button--primary" type="button" onClick={begin}>Begin pressing</button>
          <button className="text-button" type="button" onClick={replace}>Replace source</button>
        </div>
      </section>
    </main>
  );
}

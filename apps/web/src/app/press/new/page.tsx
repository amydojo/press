"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { createPressing } from "@/lib/pressings";

const DRAFT_KEY = "press:capture-draft:v1";
const EMPTY_DRAFT = { sourceUrl: "", sourceDomain: "", sourceTitle: "", selectedFragment: "", personalNote: "" };
const DEMO = {
  sourceUrl: "https://example.com/rhythmic-editorial-modernism",
  sourceDomain: "example.com",
  sourceTitle: "Design paced like music",
  selectedFragment: "Design is paced through rhythm.",
  personalNote: "The pacing feels like music.",
};

type Draft = typeof DEMO;
type CaptureSourceType = "url" | "screenshot";

function loadDraft(): Draft {
  if (typeof window === "undefined") return EMPTY_DRAFT;
  const saved = window.localStorage.getItem(DRAFT_KEY);
  if (!saved) return EMPTY_DRAFT;
  try {
    return JSON.parse(saved) as Draft;
  } catch {
    return EMPTY_DRAFT;
  }
}

export default function NewPressingPage() {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(loadDraft);
  const [sourceType, setSourceType] = useState<CaptureSourceType>("url");
  const [uploadId, setUploadId] = useState("");
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }, [draft]);

  const urlValid = useMemo(() => {
    if (sourceType === "screenshot") return Boolean(uploadId);
    try {
      const parsed = new URL(draft.sourceUrl);
      return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch {
      return false;
    }
  }, [draft.sourceUrl, sourceType, uploadId]);
  const valid = urlValid && draft.selectedFragment.trim().length > 0 && draft.personalNote.trim().length > 0 && draft.personalNote.trim().length <= 120;

  function patch(key: keyof Draft, value: string) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setSubmitting(true);
    setStatus("Preparing your pressing…");
    try {
      const sourceUrl = sourceType === "url" ? draft.sourceUrl : null;
      const sourceDomain = sourceType === "url" ? new URL(draft.sourceUrl).hostname : "uploaded source";
      const response = await createPressing({
        sourceType,
        sourceUrl,
        sourceUploadId: sourceType === "screenshot" ? uploadId : null,
        sourceDomain,
        sourceTitle: draft.sourceTitle || null,
        selectedFragment: draft.selectedFragment,
        personalNote: draft.personalNote.trim(),
      });
      window.localStorage.removeItem(DRAFT_KEY);
      router.push(`/pressings/${response.pressing.id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "PRESS could not start this pressing. Try again.");
      setSubmitting(false);
    }
  }

  return (
    <main className="product-shell">
      <header className="product-nav"><Link href="/">PRESS</Link><Link href="/pressings">Your pressings</Link></header>
      <form className="capture-flow" onSubmit={submit} noValidate>
        <div className="capture-heading"><p className="eyebrow">New pressing</p><h1>Keep the exact thing.</h1><p>One source. One fragment. One sentence about why it mattered.</p></div>
        <section className="capture-section" aria-labelledby="source-heading">
          <div><span className="step-number">01</span><h2 id="source-heading">Source</h2></div>
          <label htmlFor="source-url">Paste something you found</label>
          <input id="source-url" type="url" value={draft.sourceUrl} onChange={(event) => { setSourceType("url"); patch("sourceUrl", event.target.value); }} placeholder="https://" aria-describedby="source-help" />
          <p id="source-help" className="helper">Public http or https links only. PRESS never bypasses access controls.</p>
          <div className="capture-actions"><button type="button" className="quiet-button" onClick={() => { setDraft(DEMO); setSourceType("url"); setStatus("Demo source loaded. This is a fixture, not a live fetch."); }}>Use demo source</button><label className="quiet-button upload-button">Upload screenshot<input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { const file = event.target.files?.[0]; if (!file) return; if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 8_000_000) { setStatus("Use a PNG, JPEG, or WEBP smaller than 8 MB."); return; } setSourceType("screenshot"); setUploadId(`local:${file.name}:${file.size}`); setStatus("Screenshot selected. Production upload is delegated to the generation service."); }} /></label></div>
        </section>
        <section className="capture-section" aria-labelledby="fragment-heading">
          <div><span className="step-number">02</span><h2 id="fragment-heading">What part do you want to keep?</h2></div>
          <textarea value={draft.selectedFragment} onChange={(event) => patch("selectedFragment", event.target.value)} rows={4} required />
          <p className="helper">PRESS preserves this exactly as confirmed.</p>
        </section>
        <section className="capture-section" aria-labelledby="note-heading">
          <div><span className="step-number">03</span><h2 id="note-heading">What made you stop?</h2></div>
          <textarea value={draft.personalNote} onChange={(event) => patch("personalNote", event.target.value)} rows={3} maxLength={120} required aria-describedby="note-help note-count" />
          <div className="field-footer"><p id="note-help" className="helper">One sentence is enough.</p><p id="note-count" className="helper">{draft.personalNote.length}/120</p></div>
        </section>
        <div className="capture-submit"><button className="primary-button" type="submit" disabled={!valid || submitting}>{submitting ? "Pressing…" : "Press this"}</button><p role="status" aria-live="polite">{status}</p></div>
      </form>
    </main>
  );
}
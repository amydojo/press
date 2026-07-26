"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useRef, useState } from "react";

import { browserRepository, MAX_SOURCE_LENGTH, MIN_SOURCE_LENGTH, normalizeSource, validateSource } from "@/lib/pressings";

export default function HomePage() {
  const router = useRouter();
  const submitting = useRef(false);
  const [value, setValue] = useState("");
  const [touched, setTouched] = useState(false);
  const normalized = useMemo(() => normalizeSource(value), [value]);
  const error = validateSource(value);
  const invalid = Boolean(error);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    if (invalid || submitting.current) return;
    submitting.current = true;
    try {
      const pressing = browserRepository().create(normalized);
      router.push(`/pressings/${pressing.id}/registered`);
    } catch {
      submitting.current = false;
    }
  }

  return (
    <main className="page-shell page-shell--top">
      <header className="site-header">
        <Link href="/" className="brand" aria-label="PRESS home">PRESS</Link>
        <Link href="/archive" className="quiet-link">Archive</Link>
      </header>
      <section className="intake" aria-labelledby="intake-title">
        <div>
          <p className="eyebrow">Text intake · local fixture</p>
          <h1 id="intake-title" className="display">What made<br />you stop?</h1>
          <p className="lede">PRESS will preserve the signal, not reproduce the source.</p>
        </div>
        <form className="intake-form" onSubmit={submit} noValidate>
          <label htmlFor="source">Fragment</label>
          <div className="intake-tray">
            <textarea
              id="source"
              name="source"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              onBlur={() => setTouched(true)}
              minLength={MIN_SOURCE_LENGTH}
              maxLength={MAX_SOURCE_LENGTH}
              rows={8}
              autoCapitalize="sentences"
              enterKeyHint="done"
              aria-describedby="source-help source-error source-count"
              aria-invalid={touched && invalid}
              placeholder="Place one text fragment here."
            />
            <div className="tray-meta"><span>TXT / REGISTERED MATERIAL</span><span id="source-count">{normalized.length}/{MAX_SOURCE_LENGTH}</span></div>
          </div>
          <p id="source-help" className="field-help">Between {MIN_SOURCE_LENGTH} and {MAX_SOURCE_LENGTH} characters. Internal line breaks are preserved.</p>
          <p id="source-error" className="field-error" role="alert">{touched ? error : ""}</p>
          <button className="button button--primary" type="submit" disabled={invalid || submitting.current}>Make a pressing</button>
        </form>
      </section>
    </main>
  );
}

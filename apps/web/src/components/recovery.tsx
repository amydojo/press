import Link from "next/link";

export function Recovery({ title, message, onRemove }: { title: string; message: string; onRemove?: () => void }) {
  return (
    <main className="page-shell page-shell--top">
      <header className="site-header"><Link href="/" className="brand">PRESS</Link><Link href="/archive" className="quiet-link">Archive</Link></header>
      <section className="recovery" aria-labelledby="recovery-title">
        <p className="eyebrow">Recovery</p>
        <h1 id="recovery-title" className="display-small">{title}</h1>
        <p>{message}</p>
        <div className="action-row">
          <Link className="button" href="/">Return to intake</Link>
          <Link className="button button--secondary" href="/archive">View archive</Link>
          {onRemove && <button className="text-button" type="button" onClick={onRemove}>Remove damaged local record</button>}
        </div>
      </section>
    </main>
  );
}

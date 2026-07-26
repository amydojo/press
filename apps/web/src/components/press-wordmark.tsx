import Link from "next/link";

export function PressWordmark() {
  return (
    <Link className="press-wordmark" href="/" aria-label="PRESS home">
      <span>PRESS</span>
      <small>Internet objects</small>
    </Link>
  );
}

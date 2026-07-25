import Link from "next/link";

import { SystemDiagnostics } from "@/components/system-diagnostics";

export default function SystemPage() {
  return (
    <main className="page-shell">
      <Link className="text-link back-link" href="/">← PRESS</Link>
      <SystemDiagnostics />
    </main>
  );
}

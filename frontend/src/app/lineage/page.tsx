import Link from "next/link";
import { GitBranch } from "lucide-react";

export default function LineagePage() {
  return (
    <div className="mx-auto max-w-lg text-center">
      <div className="rounded-xl border border-gray-200 bg-white p-12 shadow-sm">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-purple-100">
          <GitBranch className="h-8 w-8 text-purple-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">SQL Lineage Explorer</h1>
        <p className="mt-3 text-gray-500">
          Phase 2 — Parse SQL procedures and visualize table lifecycle graphs in Neo4j.
        </p>
        <Link
          href="/"
          className="mt-8 inline-block rounded-lg bg-primary px-6 py-2 text-sm font-medium text-white hover:bg-primary-hover"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}

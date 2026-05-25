"use client";

import Link from "next/link";
import { useState } from "react";
import { Bot, Database, GitBranch, Plus, Settings, Sparkles, TrendingUp } from "lucide-react";
import { ManageAccountsModal } from "@/components/accounts/ManageAccountsModal";
import { FeatureTile } from "@/components/home/FeatureTile";
import { MetricCard } from "@/components/home/MetricCard";

export default function HomePage() {
  const [accountsOpen, setAccountsOpen] = useState(false);

  return (
    <div className="mx-auto max-w-5xl">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Business Intelligence Platform</h1>
        <p className="mt-3 text-gray-500">
          Neo4j GraphRAG assistant for enterprise FRDs, Excel, and Word files — with
          client-isolated graph + vector search.
        </p>
      </div>

      <div className="mt-10 grid gap-6 md:grid-cols-3">
        <MetricCard label="Total Clients" value="—" icon={Database} iconBg="bg-blue-500" />
        <MetricCard label="Documents Indexed" value="—" icon={TrendingUp} iconBg="bg-green-500" />
        <MetricCard label="Avg Correctness" value="—" icon={Sparkles} iconBg="bg-yellow-500" />
      </div>

      <h2 className="mt-14 text-center text-xl font-semibold text-gray-800">
        Select a feature to start
      </h2>

      <div className="mt-8 grid gap-6 md:grid-cols-3">
        <FeatureTile
          title="Business Assistant"
          description="Chat with your documents using RAG. Upload FRDs and get section-grounded answers."
          href="/assistant"
          icon={Bot}
          iconColor="bg-blue-500"
        />
        <FeatureTile
          title="SQL Lineage Explorer"
          description="Parse procedures and visualize table lifecycle graphs."
          icon={GitBranch}
          iconColor="bg-purple-500"
          disabled
        />
        <FeatureTile
          title="Reserved"
          description="Additional intelligence features coming in a future release."
          icon={Sparkles}
          iconColor="bg-gray-400"
          disabled
        />
      </div>

      <div className="mt-10 flex flex-wrap justify-center gap-4">
        <button
          type="button"
          onClick={() => setAccountsOpen(true)}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 font-medium text-gray-800 shadow-sm hover:bg-gray-50"
        >
          <Settings className="h-5 w-5" />
          Manage Accounts
        </button>
        <Link
          href="/assistant"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-8 py-3 font-medium text-white shadow hover:bg-primary-hover"
        >
          <Plus className="h-5 w-5" />
          Open Business Assistant
        </Link>
      </div>

      <ManageAccountsModal open={accountsOpen} onClose={() => setAccountsOpen(false)} />
    </div>
  );
}

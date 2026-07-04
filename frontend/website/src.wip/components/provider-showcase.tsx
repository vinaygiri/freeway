import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";

const PROVIDERS = [
	{ name: "NVIDIA NIM", models: 42, tier: "S+ → C", free: "~40 RPM, no CC", url: "https://build.nvidia.com" },
	{ name: "Groq", models: 8, tier: "S → B", free: "30 RPM, up to 14.4K req/day", url: "https://console.groq.com/keys" },
	{ name: "Cerebras", models: 4, tier: "S+ → B", free: "30 RPM, 1M tokens/day", url: "https://cloud.cerebras.ai" },
	{ name: "Google AI Studio", models: 6, tier: "S+ → A", free: "Free quotas vary", url: "https://aistudio.google.com/apikey" },
	{ name: "GitHub Models", models: 15, tier: "S+ → C", free: "Depends on tier", url: "https://models.github.ai" },
	{ name: "Mistral", models: 7, tier: "S+ → A", free: "Experiment plan", url: "https://console.mistral.ai/api-keys" },
	{ name: "Cloudflare AI", models: 15, tier: "S+ → B", free: "10K neurons/day", url: "https://dash.cloudflare.com" },
	{ name: "OpenRouter", models: 31, tier: "S+ → C", free: "50 req/day free", url: "https://openrouter.ai/keys" },
] as const;

const TIER_COLORS: Record<string, string> = {
	"S+": "var(--tier-s-plus)",
	S: "var(--tier-s)",
	"A+": "var(--tier-a-plus)",
	A: "var(--tier-a)",
	B: "var(--tier-b)",
	C: "var(--tier-c)",
};

function TierBadge({ tier }: { tier: string }) {
	const topTier = tier.split(" → ")[0];
	const color = TIER_COLORS[topTier] ?? "var(--text-muted)";
	return (
		<span
			className="mono text-xs px-1.5 py-0.5 rounded"
			style={{
				color,
				backgroundColor: `${color}22`,
				border: `1px solid ${color}44`,
			}}
		>
			{tier}
		</span>
	);
}

export function ProviderShowcase() {
	return (
		<section
			className="section"
			style={{
				paddingTop: 80,
				paddingBottom: 80,
				borderTop: "1px solid var(--border-subtle)",
			}}
		>
			<div className="container" style={{ maxWidth: 1100, margin: "0 auto" }}>
				<div className="flex items-end justify-between gap-4 mb-10 flex-wrap">
					<div>
						<p
							className="mono text-xs uppercase tracking-wider mb-2"
							style={{ color: "var(--text-muted)" }}
						>
							Free providers
						</p>
						<h2
							className="text-2xl sm:text-3xl font-semibold tracking-tight"
							style={{ color: "var(--text-primary)" }}
						>
							16 active providers. ~170 models.
						</h2>
					</div>
					<Link
						to="/providers"
						className="flex items-center gap-1.5 text-sm no-underline shrink-0 link-brand"
					>
						See all 16 providers
						<ArrowRight size={14} />
					</Link>
				</div>

				<div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
					{PROVIDERS.map((p) => (
						<a
							key={p.name}
							href={p.url}
							target="_blank"
							rel="noopener noreferrer"
							className="flex flex-col gap-2 p-4 rounded-md no-underline card-hover"
							style={{
								backgroundColor: "var(--bg-elevated)",
								border: "1px solid var(--border-subtle)",
							}}
						>
							<div className="flex items-start justify-between gap-2">
								<span
									className="font-medium text-sm"
									style={{ color: "var(--text-primary)" }}
								>
									{p.name}
								</span>
								<TierBadge tier={p.tier} />
							</div>
							<p className="mono text-xs" style={{ color: "var(--text-muted)" }}>
								{p.models} models
							</p>
							<p className="text-xs" style={{ color: "var(--text-secondary)" }}>
								{p.free}
							</p>
						</a>
					))}
				</div>
			</div>
		</section>
	);
}

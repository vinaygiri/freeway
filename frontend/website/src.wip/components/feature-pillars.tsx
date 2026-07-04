const PILLARS = [
	{
		n: "01",
		title: "Real-time stability scoring",
		body: "Avg latency alone lies. FCM measures p95 latency, jitter, spike rate, and uptime — and combines them into a 0-100 stability score. The fastest model right now is not always the most reliable one.",
	},
	{
		n: "02",
		title: "Picks your model. Writes the config.",
		body: "Select a model, press Enter. FCM writes the endpoint directly into your coding tool's config and launches it. OpenCode, Crush, Goose, Aider, Cline — under 10 seconds from install to coding.",
	},
	{
		n: "03",
		title: "Local OpenAI-compatible router",
		body: "One endpoint at localhost:19280/v1. The FCM daemon routes each request to the best available model in your set, with circuit breakers, failover, and health probes — totally transparent to your tool.",
	},
	{
		n: "04",
		title: "0 paid key required to start",
		body: "NVIDIA NIM, Groq, Cerebras, Google AI Studio — dozens of S+ and S tier models with no credit card. Add more providers at any time with P inside the TUI.",
	},
] as const;

export function FeaturePillars() {
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
				<p
					className="mono text-xs uppercase tracking-wider mb-2"
					style={{ color: "var(--text-muted)" }}
				>
					What makes it different
				</p>
				<h2
					className="text-2xl sm:text-3xl font-semibold tracking-tight mb-12"
					style={{ color: "var(--text-primary)" }}
				>
					Built for speed, reliability, and zero friction
				</h2>

				<div className="grid sm:grid-cols-2 gap-px" style={{ border: "1px solid var(--border-default)", borderRadius: 6, overflow: "hidden" }}>
					{PILLARS.map((p) => (
						<div
							key={p.n}
							className="p-8 transition-colors duration-150"
							style={{ backgroundColor: "var(--bg-elevated)" }}
							onMouseEnter={(e) => {
								(e.currentTarget as HTMLElement).style.backgroundColor = "var(--bg-subtle)";
							}}
							onMouseLeave={(e) => {
								(e.currentTarget as HTMLElement).style.backgroundColor = "var(--bg-elevated)";
							}}
						>
							<p
								className="mono text-xs mb-4"
								style={{ color: "var(--text-muted)" }}
							>
								{p.n} /
							</p>
							<h3
								className="text-lg font-semibold tracking-tight mb-3"
								style={{ color: "var(--text-primary)" }}
							>
								{p.title}
							</h3>
							<p
								className="text-sm leading-relaxed"
								style={{ color: "var(--text-secondary)" }}
							>
								{p.body}
							</p>
						</div>
					))}
				</div>
			</div>
		</section>
	);
}

import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";

const ASCII_DIAGRAM = `┌─ your coding tool ────────────┐
│  OpenCode · Crush · Goose · … │
└─────────────┬─────────────────┘
              │ http://localhost:19280/v1
              ▼
┌─ free-coding-models daemon ───┐
│  ◉ probe · ◉ score · ◉ route  │
└──┬──────┬────────┬───────┬────┘
   ▼      ▼        ▼       ▼
 NVIDIA  Groq  Cerebras  OpenRouter
  42m    8m      4m        31m`;

const CONFIG_LINES = [
	{ label: "Base URL", value: "http://localhost:19280/v1" },
	{ label: "Model   ", value: "fcm" },
	{ label: "API key ", value: "fcm-local" },
] as const;

export function RouterSection() {
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
				<div className="grid lg:grid-cols-2 gap-12 items-center">
					{/* Text side */}
					<div>
						<p
							className="mono text-xs uppercase tracking-wider mb-2"
							style={{ color: "var(--text-muted)" }}
						>
							Smart Model Router
						</p>
						<h2
							className="text-2xl sm:text-3xl font-semibold tracking-tight mb-4"
							style={{ color: "var(--text-primary)" }}
						>
							One endpoint. 16 fallbacks.
						</h2>
						<p
							className="text-sm leading-relaxed mb-6"
							style={{ color: "var(--text-secondary)", maxWidth: 480 }}
						>
							The FCM daemon runs locally and exposes an OpenAI-compatible API at{" "}
							<code
								className="px-1.5 py-0.5 rounded text-xs"
								style={{
									backgroundColor: "var(--bg-subtle)",
									color: "var(--brand)",
									border: "1px solid var(--border-subtle)",
								}}
							>
								localhost:19280/v1
							</code>
							. It probes all your configured providers in real time, scores them,
							and routes each request to the healthiest model — with automatic
							failover on 429s, timeouts, and auth errors.
						</p>

						<div
							className="rounded-md p-4 mb-6 mono text-sm"
							style={{
								backgroundColor: "var(--bg-elevated)",
								border: "1px solid var(--border-default)",
							}}
						>
							{CONFIG_LINES.map((line) => (
								<div key={line.label} className="flex gap-2">
									<span style={{ color: "var(--text-muted)" }}>{line.label}:</span>
									<span style={{ color: "var(--brand)" }}>{line.value}</span>
								</div>
							))}
						</div>

						<Link
							to="/docs/router"
							className="flex items-center gap-1.5 text-sm no-underline link-brand"
						>
							Router docs
							<ArrowRight size={14} />
						</Link>
					</div>

					{/* Diagram side */}
					<div
						className="rounded-md p-6 mono text-sm leading-relaxed"
						style={{
							backgroundColor: "var(--bg-elevated)",
							border: "1px solid var(--border-default)",
							color: "var(--text-secondary)",
							whiteSpace: "pre",
							overflowX: "auto",
						}}
					>
						{ASCII_DIAGRAM}
					</div>
				</div>
			</div>
		</section>
	);
}

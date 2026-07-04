import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { TerminalBlock } from "./terminal-block";

const CARDS = [
	{
		title: "Local TUI",
		description:
			"Ping all models in parallel, pick the fastest, configure your tool — in under 10 seconds.",
		lines: [
			{ type: "command" as const, text: "npm install -g free-coding-models" },
			{ type: "command" as const, text: "free-coding-models" },
		],
		href: "/docs/quickstart" as const,
	},
	{
		title: "Docker",
		description:
			"Run the daemon + web dashboard without installing Node.js. Mount your keys, point your tool at localhost.",
		lines: [
			{ type: "command" as const, text: "docker run -p 19280:19280 \\" },
			{ type: "output" as const, text: "  -e OPENROUTER_API_KEY=... \\" },
			{ type: "output" as const, text: "  ghcr.io/vava-nessa/free-coding-models:latest" },
		],
		href: "/docs/docker" as const,
	},
	{
		title: "Background daemon",
		description:
			"One persistent endpoint. The daemon routes every request to the best live model, with failover and circuit breakers.",
		lines: [
			{ type: "command" as const, text: "free-coding-models --daemon-bg" },
			{ type: "blank" as const },
			{ type: "output" as const, text: "Base URL: http://localhost:19280/v1" },
			{ type: "output" as const, text: "Model:    fcm" },
			{ type: "output" as const, text: "API key:  fcm-local" },
		],
		href: "/docs/router" as const,
	},
] as const;

export function DeploymentCards() {
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
					Three ways to run it
				</p>
				<h2
					className="text-2xl sm:text-3xl font-semibold tracking-tight mb-10"
					style={{ color: "var(--text-primary)" }}
				>
					Pick the setup that fits your workflow
				</h2>

				<div className="grid sm:grid-cols-3 gap-4">
					{CARDS.map((card) => (
						<div
							key={card.title}
							className="flex flex-col rounded-md overflow-hidden"
							style={{ border: "1px solid var(--border-default)" }}
						>
							<div className="p-6 flex-1">
								<h3
									className="font-semibold text-base mb-2 tracking-tight"
									style={{ color: "var(--text-primary)" }}
								>
									{card.title}
								</h3>
								<p
									className="text-sm leading-relaxed mb-4"
									style={{ color: "var(--text-secondary)" }}
								>
									{card.description}
								</p>
							</div>
							<div
								className="p-4"
								style={{ borderTop: "1px solid var(--border-subtle)" }}
							>
								<TerminalBlock lines={card.lines} className="mb-4" />
								<Link
									to={card.href}
									className="flex items-center gap-1 text-xs no-underline link-brand"
								>
									View guide
									<ArrowRight size={12} />
								</Link>
							</div>
						</div>
					))}
				</div>
			</div>
		</section>
	);
}

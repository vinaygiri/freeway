import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { TerminalBlock } from "./terminal-block";

const INSTALL_LINES = [
	{ type: "command" as const, text: "npm install -g free-coding-models" },
	{ type: "command" as const, text: "free-coding-models" },
	{ type: "blank" as const },
	{ type: "output" as const, text: "✓ pinging 170 models in parallel..." },
	{ type: "output" as const, text: "✓ Kimi K2 · NVIDIA NIM · 142ms · stability 96  🥇" },
	{ type: "output" as const, text: "✓ DeepSeek V3.1 · Groq · 198ms · stability 91  🥈" },
	{ type: "output" as const, text: "✓ Qwen3-235B · Cerebras · 211ms · stability 88  🥉" },
];

const BADGES = [
	"https://img.shields.io/npm/v/free-coding-models?color=3d6b00&label=npm&logo=npm",
	"https://img.shields.io/node/v/free-coding-models?color=3d6b00&logo=node.js",
	"https://img.shields.io/npm/l/free-coding-models?color=3d6b00",
	"https://img.shields.io/badge/models-170+-3d6b00?logo=nvidia",
	"https://img.shields.io/badge/providers-16-1a56db",
] as const;

export function Hero() {
	return (
		<section className="section" style={{ paddingTop: 80, paddingBottom: 80 }}>
			<div className="container" style={{ maxWidth: 860, margin: "0 auto" }}>
				{/* Logo + wordmark */}
				<div className="flex items-center gap-3 mb-6 animate-fade-up">
					<img
						src="/logo.webp"
						alt="free-coding-models logo"
						width={52}
						height={52}
						className="rounded-md"
					/>
					<h1
						className="mono text-2xl sm:text-3xl font-semibold tracking-tight"
						style={{ color: "var(--text-primary)" }}
					>
						free-coding-models
					</h1>
				</div>

				{/* Subtitle — from the README */}
				<p
					className="text-3xl sm:text-4xl font-semibold tracking-tight leading-tight mb-4 animate-fade-up"
					style={{ color: "var(--text-primary)", animationDelay: "60ms" }}
				>
					Find the fastest free coding model in seconds
				</p>

				<p
					className="text-base sm:text-lg mb-10 animate-fade-up"
					style={{
						color: "var(--text-secondary)",
						maxWidth: 600,
						animationDelay: "120ms",
					}}
				>
					Track ~170 models across ~15 trusted free or free-limited AI providers
					in real time. Install free API endpoints to your favorite AI coding
					tools: OpenCode, Crush, Goose, Aider, Cline, and more.
				</p>

				{/* CTAs */}
				<div
					className="flex flex-wrap items-center gap-3 mb-10 animate-fade-up"
					style={{ animationDelay: "180ms" }}
				>
					<Link
						to="/docs/quickstart"
						className="flex items-center gap-1.5 px-5 py-2.5 rounded font-semibold text-sm no-underline btn-brand"
					>
						Quick start
						<ArrowRight size={14} />
					</Link>
					<Link
						to="/docs"
						className="flex items-center gap-1.5 px-5 py-2.5 rounded font-semibold text-sm no-underline btn-ghost"
					>
						Read the docs
					</Link>
					<a
						href="https://discord.gg/ZTNFHvvCkU"
						target="_blank"
						rel="noopener noreferrer"
						className="flex items-center gap-1.5 px-5 py-2.5 rounded font-semibold text-sm no-underline link-secondary hover-text-primary"
						style={{ border: "1px solid var(--border-default)" }}
					>
						💬 Discord
					</a>
				</div>

				{/* npm badges */}
				<div
					className="flex flex-wrap items-center gap-2 mb-10 animate-fade-up"
					style={{ animationDelay: "220ms" }}
				>
					{BADGES.map((src) => (
						<img key={src} src={src} alt="" height={20} />
					))}
				</div>

				{/* Terminal block */}
				<div className="animate-fade-up" style={{ animationDelay: "280ms" }}>
					<TerminalBlock
						lines={INSTALL_LINES}
						copyText={"npm install -g free-coding-models\nfree-coding-models"}
					/>
				</div>
			</div>
		</section>
	);
}

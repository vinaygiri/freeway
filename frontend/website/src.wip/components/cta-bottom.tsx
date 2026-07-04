import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";

export function CtaBottom() {
	return (
		<section
			className="section"
			style={{
				paddingTop: 96,
				paddingBottom: 96,
				borderTop: "1px solid var(--border-subtle)",
			}}
		>
			<div
				className="container text-center"
				style={{ maxWidth: 600, margin: "0 auto" }}
			>
				<div className="flex items-center justify-center gap-3 mb-5">
					<img
						src="/logo.webp"
						alt="free-coding-models"
						width={40}
						height={40}
						className="rounded-sm"
					/>
					<span
						className="mono text-xl font-semibold tracking-tight"
						style={{ color: "var(--text-primary)" }}
					>
						free-coding-models
					</span>
				</div>

				<p
					className="text-2xl sm:text-3xl font-semibold tracking-tight mb-4"
					style={{ color: "var(--text-primary)" }}
				>
					Find the fastest free coding model in seconds
				</p>

				<p className="text-sm mb-8" style={{ color: "var(--text-secondary)" }}>
					Free forever. No credit card. No telemetry by default.
				</p>

				<div className="flex flex-wrap items-center justify-center gap-3">
					<Link
						to="/docs/quickstart"
						className="flex items-center gap-1.5 px-6 py-3 rounded font-semibold text-sm no-underline btn-brand"
					>
						Quick start
						<ArrowRight size={14} />
					</Link>
					<Link
						to="/docs"
						className="flex items-center gap-1.5 px-6 py-3 rounded font-semibold text-sm no-underline btn-ghost"
					>
						Read the docs
					</Link>
				</div>
			</div>
		</section>
	);
}

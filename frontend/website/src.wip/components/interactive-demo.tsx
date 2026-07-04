import { Terminal } from "lucide-react";

// 📖 Placeholder for the interactive live demo section.
// Will become an embedded terminal simulation (xterm.js or CSS-animated)
// showing real-time model pings, tier filtering, and tool launch flow.
export function InteractiveDemo() {
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
					Try it live
				</p>
				<h2
					className="text-2xl sm:text-3xl font-semibold tracking-tight mb-10"
					style={{ color: "var(--text-primary)" }}
				>
					Interactive demo
				</h2>

				{/* Placeholder */}
				<div
					className="relative flex flex-col items-center justify-center rounded-md overflow-hidden"
					style={{
						border: "1px dashed var(--border-emphasis)",
						backgroundColor: "var(--bg-elevated)",
						minHeight: 340,
					}}
				>
					{/* macOS bar */}
					<div
						className="absolute top-0 left-0 right-0 flex items-center gap-2 px-4 py-2.5"
						style={{
							backgroundColor: "var(--bg-subtle)",
							borderBottom: "1px solid var(--border-subtle)",
						}}
					>
						<div className="flex items-center gap-1.5">
							<div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#ff5f57" }} />
							<div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#febc2e" }} />
							<div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#28c840" }} />
						</div>
						<span
							className="mono text-xs"
							style={{ color: "var(--text-muted)", marginLeft: 8 }}
						>
							free-coding-models — interactive demo
						</span>
					</div>

					{/* Placeholder content */}
					<div className="flex flex-col items-center gap-4 px-8 py-12 text-center mt-8">
						<div
							className="flex items-center justify-center w-14 h-14 rounded-md"
							style={{
								backgroundColor: "var(--brand-glow)",
								border: "1px solid var(--brand-dim)",
							}}
						>
							<Terminal size={28} style={{ color: "var(--brand)" }} />
						</div>
						<p
							className="font-semibold text-lg"
							style={{ color: "var(--text-primary)" }}
						>
							Live terminal coming soon
						</p>
						<p
							className="text-sm max-w-md"
							style={{ color: "var(--text-secondary)" }}
						>
							An embedded interactive demo will let you browse models, filter by
							tier and provider, and see the stability score in action — right
							here in the browser.
						</p>
						<span
							className="mono text-xs px-3 py-1 rounded"
							style={{
								color: "var(--brand)",
								backgroundColor: "var(--brand-glow)",
								border: "1px solid var(--brand-dim)",
							}}
						>
							TODO: xterm.js / animated terminal
						</span>
					</div>
				</div>
			</div>
		</section>
	);
}

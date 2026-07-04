export function VisualDemo() {
	return (
		<section
			className="section"
			style={{ paddingTop: 0, paddingBottom: 80 }}
		>
			<div className="container" style={{ maxWidth: 1100, margin: "0 auto" }}>
				{/* Full-bleed terminal screenshot with FCM green glow */}
				<div
					className="relative rounded-md overflow-hidden"
					style={{
						border: "1px solid var(--border-default)",
						boxShadow: "0 0 0 1px var(--brand-glow), 0 0 60px 0 var(--brand-glow)",
					}}
				>
					{/* macOS bar */}
					<div
						className="flex items-center gap-2 px-4 py-2.5"
						style={{
							backgroundColor: "var(--bg-elevated)",
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
							free-coding-models — live pings
						</span>
					</div>

					{/* Demo gif/video */}
					<div
						className="relative"
						style={{ backgroundColor: "var(--bg-base)" }}
					>
						<img
							src="/demo.gif"
							alt="free-coding-models TUI — real-time model pings and stability scores"
							className="w-full block"
							style={{ display: "block" }}
						/>
					</div>
				</div>

				<p
					className="mono text-xs text-center mt-4"
					style={{ color: "var(--text-muted)" }}
				>
					Real ping. Real stability score. Real launch.
				</p>
			</div>
		</section>
	);
}

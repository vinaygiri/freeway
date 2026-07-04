import { Check, Minus } from "lucide-react";

const ROWS = [
	{ feature: "Tests 170+ models in parallel", manual: false, dashboard: false, paid: false, fcm: true },
	{ feature: "Stability score (p95 + jitter + uptime)", manual: false, dashboard: false, paid: false, fcm: true },
	{ feature: "Auto-writes tool config + launches", manual: false, dashboard: false, paid: false, fcm: true },
	{ feature: "100% free tier focused", manual: false, dashboard: false, paid: false, fcm: true },
	{ feature: "Local OpenAI-compatible router", manual: false, dashboard: false, paid: true, fcm: true },
	{ feature: "Works with 20+ coding tools", manual: false, dashboard: false, paid: false, fcm: true },
	{ feature: "No signup, no account", manual: true, dashboard: false, paid: false, fcm: true },
	{ feature: "Telemetry off by default", manual: true, dashboard: false, paid: false, fcm: true },
] as const;

function Cell({ value, highlighted }: { value: boolean; highlighted?: boolean }) {
	return (
		<td
			className="py-3 px-4 text-center"
			style={{
				borderLeft: highlighted ? "1px solid var(--brand-dim)" : "1px solid var(--border-subtle)",
				borderRight: highlighted ? "1px solid var(--brand-dim)" : undefined,
				backgroundColor: highlighted ? "rgba(118,185,0,0.03)" : undefined,
			}}
		>
			{value ? (
				<Check size={15} style={{ color: "var(--brand)", margin: "0 auto" }} />
			) : (
				<Minus size={15} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
			)}
		</td>
	);
}

export function ComparisonTable() {
	return (
		<section className="section" style={{ paddingTop: 80, paddingBottom: 80 }}>
			<div className="container" style={{ maxWidth: 1000, margin: "0 auto" }}>
				<p
					className="mono text-xs uppercase tracking-wider mb-2"
					style={{ color: "var(--text-muted)" }}
				>
					Why free-coding-models
				</p>
				<h2
					className="text-2xl sm:text-3xl font-semibold tracking-tight mb-10"
					style={{ color: "var(--text-primary)" }}
				>
					Not all free model tools are equal
				</h2>

				<div className="overflow-x-auto rounded-md" style={{ border: "1px solid var(--border-default)" }}>
					<table className="w-full text-sm border-collapse">
						<thead>
							<tr style={{ borderBottom: "1px solid var(--border-default)" }}>
								<th
									className="py-3 px-4 text-left font-medium"
									style={{
										color: "var(--text-muted)",
										backgroundColor: "var(--bg-elevated)",
									}}
								>
									Feature
								</th>
								{[
									{ label: "Manual key juggling", highlighted: false },
									{ label: "Provider dashboards", highlighted: false },
									{ label: "Paid routers", highlighted: false },
									{ label: "free-coding-models", highlighted: true },
								].map((col) => (
									<th
										key={col.label}
										className="py-3 px-4 text-center font-medium text-xs"
										style={{
											color: col.highlighted ? "var(--brand)" : "var(--text-muted)",
											backgroundColor: col.highlighted
												? "rgba(118,185,0,0.05)"
												: "var(--bg-elevated)",
											borderLeft: col.highlighted
												? "1px solid var(--brand-dim)"
												: "1px solid var(--border-subtle)",
											borderRight: col.highlighted
												? "1px solid var(--brand-dim)"
												: undefined,
											borderTop: col.highlighted
												? "2px solid var(--brand)"
												: undefined,
											fontFamily: col.highlighted ? "monospace" : undefined,
										}}
									>
										{col.label}
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{ROWS.map((row, i) => (
								<tr
									key={row.feature}
									style={{
										borderBottom:
											i < ROWS.length - 1
												? "1px solid var(--border-subtle)"
												: undefined,
										backgroundColor:
											i % 2 === 0 ? "var(--bg-base)" : "var(--bg-subtle)",
									}}
								>
									<td
										className="py-3 px-4"
										style={{ color: "var(--text-secondary)" }}
									>
										{row.feature}
									</td>
									<Cell value={row.manual} />
									<Cell value={row.dashboard} />
									<Cell value={row.paid} />
									<Cell value={row.fcm} highlighted />
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</div>
		</section>
	);
}

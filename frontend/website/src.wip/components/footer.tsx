import { Link } from "@tanstack/react-router";
import { Github, MessageCircle, Rss } from "lucide-react";

const COLUMNS = [
	{
		title: "Product",
		links: [
			{ label: "Quick start", href: "/docs/quickstart" },
			{ label: "Providers", href: "/providers" },
			{ label: "Models", href: "/models" },
			{ label: "Tools", href: "/tools" },
			{ label: "Changelog", href: "/changelog" },
		],
	},
	{
		title: "Docs",
		links: [
			{ label: "CLI flags", href: "/docs/cli" },
			{ label: "Config & API keys", href: "/docs/config" },
			{ label: "Smart Model Router", href: "/docs/router" },
			{ label: "Docker", href: "/docs/docker" },
			{ label: "Stability score", href: "/docs/stability" },
			{ label: "Contributing", href: "/docs/development" },
		],
	},
	{
		title: "Community",
		links: [
			{
				label: "Discord",
				href: "https://discord.gg/ZTNFHvvCkU",
				external: true,
			},
			{
				label: "GitHub",
				href: "https://github.com/vava-nessa/free-coding-models",
				external: true,
			},
			{
				label: "Blog",
				href: "/blog",
			},
			{
				label: "RSS feed",
				href: "/blog/feed.xml",
			},
		],
	},
	{
		title: "Legal",
		links: [
			{ label: "MIT License", href: "/legal/license" },
			{ label: "Security policy", href: "/security" },
			{ label: "Privacy / Telemetry", href: "/docs/config#telemetry" },
		],
	},
] as const;

export function Footer() {
	return (
		<footer
			className="border-t"
			style={{ borderColor: "var(--border-subtle)" }}
		>
			<div
				className="container"
				style={{ maxWidth: 1280, margin: "0 auto", padding: "64px 24px 48px" }}
			>
				{/* Top: wordmark + cols */}
				<div className="grid gap-12 md:grid-cols-[220px_1fr]">
					{/* Brand */}
					<div>
						<div className="flex items-center gap-2 mb-3">
							<img
								src="/logo.webp"
								alt="free-coding-models"
								width={24}
								height={24}
								className="rounded-sm"
							/>
							<span
								className="mono text-sm font-semibold"
								style={{ color: "var(--text-primary)" }}
							>
								free-coding-models
							</span>
						</div>
						<p className="text-sm" style={{ color: "var(--text-secondary)" }}>
							Find the fastest free coding model in seconds.
						</p>
						<div className="flex items-center gap-3 mt-4">
							<a
								href="https://discord.gg/ZTNFHvvCkU"
								target="_blank"
								rel="noopener noreferrer"
								title="Discord"
								style={{ color: "var(--text-muted)" }}
								className="transition-colors duration-150 hover:text-[var(--text-primary)]"
							>
								<MessageCircle size={16} />
							</a>
							<a
								href="https://github.com/vava-nessa/free-coding-models"
								target="_blank"
								rel="noopener noreferrer"
								title="GitHub"
								style={{ color: "var(--text-muted)" }}
								className="transition-colors duration-150 hover:text-[var(--text-primary)]"
							>
								<Github size={16} />
							</a>
							<a
								href="/blog/feed.xml"
								title="RSS feed"
								style={{ color: "var(--text-muted)" }}
								className="transition-colors duration-150 hover:text-[var(--text-primary)]"
							>
								<Rss size={16} />
							</a>
						</div>
					</div>

					{/* Columns */}
					<div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
						{COLUMNS.map((col) => (
							<div key={col.title}>
								<p
									className="mono text-xs font-semibold uppercase tracking-wider mb-3"
									style={{ color: "var(--text-muted)" }}
								>
									{col.title}
								</p>
								<ul className="space-y-2">
									{col.links.map((link) => (
										<li key={link.label}>
											{"external" in link && link.external ? (
												<a
													href={link.href}
													target="_blank"
													rel="noopener noreferrer"
													className="text-sm no-underline transition-colors duration-150"
													style={{ color: "var(--text-secondary)" }}
													onMouseEnter={(e) => {
														(e.currentTarget as HTMLElement).style.color =
															"var(--text-primary)";
													}}
													onMouseLeave={(e) => {
														(e.currentTarget as HTMLElement).style.color =
															"var(--text-secondary)";
													}}
												>
													{link.label}
												</a>
											) : (
												<Link
													to={link.href as string}
													className="text-sm no-underline transition-colors duration-150"
													style={{ color: "var(--text-secondary)" }}
													activeProps={{
														style: { color: "var(--text-primary)" },
													}}
												>
													{link.label}
												</Link>
											)}
										</li>
									))}
								</ul>
							</div>
						))}
					</div>
				</div>

				{/* Bottom bar */}
				<div
					className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mt-12 pt-6 border-t"
					style={{ borderColor: "var(--border-subtle)" }}
				>
					<p
						className="mono text-xs"
						style={{ color: "var(--text-muted)" }}
					>
						© {new Date().getFullYear()} free-coding-models · MIT License
					</p>
					<p className="text-xs" style={{ color: "var(--text-muted)" }}>
						Made with ❤️ by{" "}
						<a
							href="https://vanessadepraute.dev"
							target="_blank"
							rel="noopener noreferrer"
							style={{ color: "var(--text-secondary)" }}
						>
							Vanessa Depraute
						</a>{" "}
						(
						<a
							href="https://vavanessa.dev"
							target="_blank"
							rel="noopener noreferrer"
							style={{ color: "var(--text-secondary)" }}
						>
							Vava-Nessa
						</a>
						)
					</p>
				</div>
			</div>
		</footer>
	);
}

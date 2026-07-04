import { Link } from "@tanstack/react-router";
import { Github, MessageCircle } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

const NAV_LINKS = [
	{ to: "/docs" as const, label: "Docs" },
	{ to: "/blog" as const, label: "Blog" },
	{ to: "/providers" as const, label: "Providers" },
	{ to: "/models" as const, label: "Models" },
	{ to: "/changelog" as const, label: "Changelog" },
];

export function Nav() {
	return (
		<header
			className="sticky top-0 z-50 h-14 border-b backdrop-blur-sm"
			style={{
				borderColor: "var(--border-subtle)",
				backgroundColor: "var(--bg-overlay)",
			}}
		>
			<div
				className="flex h-full items-center justify-between gap-4"
				style={{ maxWidth: 1280, margin: "0 auto", padding: "0 24px" }}
			>
				{/* Wordmark */}
				<Link
					to="/"
					className="flex items-center gap-2.5 shrink-0 no-underline"
					style={{ color: "var(--text-primary)" }}
				>
					<img
						src="/logo.webp"
						alt="free-coding-models"
						width={28}
						height={28}
						className="rounded-sm"
					/>
					<span
						className="mono text-sm font-semibold tracking-tight hidden sm:inline"
						style={{ color: "var(--text-primary)" }}
					>
						free-coding-models
					</span>
				</Link>

				{/* Nav links */}
				<nav className="hidden md:flex items-center gap-1">
					{NAV_LINKS.map((link) => (
						<Link
							key={link.to}
							to={link.to}
							className="px-3 py-1.5 rounded text-sm transition-colors duration-150 no-underline link-secondary hover-text-primary hover-bg-subtle"
							activeProps={{ className: "px-3 py-1.5 rounded text-sm transition-colors duration-150 no-underline font-medium" }}
							activeOptions={{ exact: link.to === "/" }}
						>
							{link.label}
						</Link>
					))}
				</nav>

				{/* Right side actions */}
				<div className="flex items-center gap-2 shrink-0">
					<a
						href="https://discord.gg/ZTNFHvvCkU"
						target="_blank"
						rel="noopener noreferrer"
						title="Discord"
						className="flex items-center justify-center w-8 h-8 rounded transition-colors duration-150 link-muted hover-text-primary hover-bg-subtle"
					>
						<MessageCircle size={16} />
					</a>
					<a
						href="https://github.com/vava-nessa/free-coding-models"
						target="_blank"
						rel="noopener noreferrer"
						className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs no-underline link-secondary hover-text-primary hover-border-emphasis"
						style={{ border: "1px solid var(--border-default)" }}
					>
						<Github size={13} />
						<span>GitHub</span>
					</a>
					<Link
						to="/docs/quickstart"
						className="px-3 py-1 rounded text-xs font-semibold no-underline btn-brand"
					>
						Install
					</Link>
					<ThemeToggle />
				</div>
			</div>
		</header>
	);
}

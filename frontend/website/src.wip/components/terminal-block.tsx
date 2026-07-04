import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { cn } from "#/lib/utils";

interface TerminalLine {
	type: "command" | "output" | "blank";
	text?: string;
}

interface TerminalBlockProps {
	title?: string;
	lines: TerminalLine[];
	copyText?: string;
	className?: string;
}

export function TerminalBlock({
	title = "free-coding-models",
	lines,
	copyText,
	className,
}: TerminalBlockProps) {
	const [copied, setCopied] = useState(false);

	async function handleCopy() {
		const text = copyText ?? lines.filter(l => l.type === "command").map(l => l.text).join("\n");
		await navigator.clipboard.writeText(text);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	}

	return (
		<div
			className={cn("rounded-md overflow-hidden", className)}
			style={{ border: "1px solid var(--border-default)" }}
		>
			{/* macOS-style title bar */}
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
					className="mono text-xs flex-1 text-center"
					style={{ color: "var(--text-muted)" }}
				>
					{title}
				</span>
				{copyText !== undefined && (
					<button
						type="button"
						onClick={handleCopy}
						title="Copy to clipboard"
						className="flex items-center gap-1 transition-colors duration-150"
						style={{ color: "var(--text-muted)" }}
						onMouseEnter={(e) => {
							(e.currentTarget as HTMLElement).style.color = "var(--text-primary)";
						}}
						onMouseLeave={(e) => {
							(e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
						}}
					>
						{copied ? <Check size={13} /> : <Copy size={13} />}
					</button>
				)}
			</div>

			{/* Terminal body */}
			<div
				className="px-5 py-4 font-mono text-sm leading-relaxed"
				style={{ backgroundColor: "var(--bg-base)" }}
			>
				{lines.map((line, i) => (
					// biome-ignore lint/suspicious/noArrayIndexKey: static terminal lines
					<div key={i} className="flex items-start gap-2">
						{line.type === "command" && (
							<>
								<span
									className="select-none shrink-0 mt-0.5"
									style={{ color: "var(--brand)" }}
								>
									$
								</span>
								<span style={{ color: "var(--text-primary)" }}>{line.text}</span>
							</>
						)}
						{line.type === "output" && (
							<span
								className="pl-5"
								style={{ color: "var(--text-secondary)" }}
							>
								{line.text}
							</span>
						)}
						{line.type === "blank" && <span className="h-4" />}
					</div>
				))}
			</div>
		</div>
	);
}

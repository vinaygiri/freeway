import { useEffect, useState } from "react";
import { Moon, Sun, Monitor } from "lucide-react";

type Theme = "auto" | "dark" | "light";

const THEMES: Theme[] = ["auto", "dark", "light"];

const ICONS = {
	auto: Monitor,
	dark: Moon,
	light: Sun,
} as const;

function applyTheme(theme: Theme) {
	const root = document.documentElement;
	const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
	const isDark = theme === "dark" || (theme === "auto" && prefersDark);
	root.classList.toggle("light", !isDark);
}

// Easter egg: pressing G cycles theme like in the TUI
export function useThemeKeyboard(cycle: () => void) {
	useEffect(() => {
		function onKey(e: KeyboardEvent) {
			const tag = (e.target as HTMLElement).tagName;
			if (tag === "INPUT" || tag === "TEXTAREA") return;
			if (e.key === "g" || e.key === "G") cycle();
		}
		window.addEventListener("keydown", onKey);
		return () => window.removeEventListener("keydown", onKey);
	}, [cycle]);
}

export function ThemeToggle() {
	const [theme, setTheme] = useState<Theme>(() => {
		if (typeof window === "undefined") return "auto";
		return (localStorage.getItem("fcm-theme") as Theme) ?? "auto";
	});

	useEffect(() => {
		applyTheme(theme);
		localStorage.setItem("fcm-theme", theme);
	}, [theme]);

	// Re-apply on system preference change when in auto mode
	useEffect(() => {
		const mq = window.matchMedia("(prefers-color-scheme: dark)");
		const handler = () => { if (theme === "auto") applyTheme("auto"); };
		mq.addEventListener("change", handler);
		return () => mq.removeEventListener("change", handler);
	}, [theme]);

	function cycle() {
		setTheme((t) => THEMES[(THEMES.indexOf(t) + 1) % THEMES.length]);
	}

	useThemeKeyboard(cycle);

	const Icon = ICONS[theme];

	return (
		<button
			type="button"
			onClick={cycle}
			title={`Theme: ${theme} (press G to cycle)`}
			className="flex items-center justify-center w-8 h-8 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors duration-150"
		>
			<Icon size={16} />
		</button>
	);
}

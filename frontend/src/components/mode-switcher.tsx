import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"

function MoonThemeIcon() {
    return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round"
            strokeLinejoin="round" aria-hidden="true" focusable="false">
            <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z" />
        </svg>
    )
}

function SunThemeIcon() {
    return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round"
            strokeLinejoin="round" aria-hidden="true" focusable="false">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
        </svg>
    )
}

export function ModeSwitcher() {
    const { resolvedTheme, setTheme } = useTheme()
    const nextTheme = resolvedTheme === "dark" ? "light" : "dark"
    const label = nextTheme === "dark" ? "切换到深色主题" : "切换到浅色主题"

    return (
        <Button
            type="button"
            variant="ghost"
            className="auth-theme-toggle h-9 w-9 px-0"
            onClick={() => setTheme(nextTheme)}
            aria-label={label}
            title={label}
        >
            {resolvedTheme === "dark"
                ? <SunThemeIcon />
                : <MoonThemeIcon />}
        </Button>
    )
}

import { MoonIcon, SunIcon } from "lucide-react"

import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"

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
                ? <SunIcon aria-hidden="true" />
                : <MoonIcon aria-hidden="true" />}
        </Button>
    )
}

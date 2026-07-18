import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"

export type Theme = "system" | "dark" | "light"
export type ResolvedTheme = "dark" | "light"

type ThemeProviderProps = {
    children: React.ReactNode
    defaultTheme?: Theme
    storageKey?: string
}

type ThemeProviderState = {
    theme: Theme
    resolvedTheme: ResolvedTheme
    setTheme: (theme: Theme) => void
}

const initialState: ThemeProviderState = {
    theme: "system",
    resolvedTheme: "light",
    setTheme: () => null,
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)
const SYSTEM_THEME_QUERY = "(prefers-color-scheme: dark)"
const VALID_THEMES = new Set<Theme>(["system", "light", "dark"])

const isTheme = (value: string | null): value is Theme => (
    value !== null && VALID_THEMES.has(value as Theme)
)

const resolveTheme = (theme: Theme): ResolvedTheme => (
    theme === "system"
        ? (window.matchMedia(SYSTEM_THEME_QUERY).matches ? "dark" : "light")
        : theme
)

export function ThemeProvider({
    children,
    defaultTheme = "system",
    storageKey = "nf-theme",
    ...props
}: ThemeProviderProps) {
    const readInitialTheme = () => {
        const storedTheme = localStorage.getItem(storageKey)
        if (isTheme(storedTheme)) return storedTheme

        const legacyTheme = localStorage.getItem("vite-ui-theme")
        return isTheme(legacyTheme) ? legacyTheme : defaultTheme
    }

    const [theme, setThemeState] = useState<Theme>(readInitialTheme)
    const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => resolveTheme(readInitialTheme()))

    useEffect(() => {
        const root = window.document.documentElement
        const media = window.matchMedia(SYSTEM_THEME_QUERY)

        const applyTheme = () => {
            const nextResolvedTheme = theme === "system"
                ? (media.matches ? "dark" : "light")
                : theme

            root.classList.remove("light", "dark")
            root.classList.add(nextResolvedTheme)
            root.dataset.theme = theme
            root.dataset.resolvedTheme = nextResolvedTheme
            root.style.colorScheme = nextResolvedTheme
            setResolvedTheme(nextResolvedTheme)

            const themeColor = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
            themeColor?.setAttribute("content", nextResolvedTheme === "dark" ? "#302d29" : "#c3dfe0")
        }

        applyTheme()
        if (theme === "system") media.addEventListener("change", applyTheme)

        return () => media.removeEventListener("change", applyTheme)
    }, [theme])

    const setTheme = useCallback((nextTheme: Theme) => {
        localStorage.setItem(storageKey, nextTheme)
        localStorage.removeItem("vite-ui-theme")
        setThemeState(nextTheme)
    }, [storageKey])

    const value = useMemo(() => ({
        theme,
        resolvedTheme,
        setTheme,
    }), [resolvedTheme, setTheme, theme])

    return (
        <ThemeProviderContext.Provider {...props} value={value}>
            {children}
        </ThemeProviderContext.Provider>
    )
}

export const useTheme = () => {
    const context = useContext(ThemeProviderContext)

    if (context === undefined)
        throw new Error("useTheme must be used within a ThemeProvider")

    return context
}

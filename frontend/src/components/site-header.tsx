import { ModeSwitcher } from "@/components/mode-switcher";
import { Button } from "@/components/ui/button";
import { Icons } from "@/components/icons";


export function SiteHeader() {
    return (
        <header className="auth-header sticky top-0 z-50 w-full border-b">
            <div className="auth-header-inner flex h-16 items-center justify-between">
                <a className="auth-brand" href="https://live.neofantasy.online/index/" aria-label="返回 NeoFantasy Live">
                    <img src="/rabbit-logo.png" alt="" width="38" height="38" />
                    <span><span>NeoFantasy</span><small>ACCOUNT</small></span>
                </a>
                <div className="flex flex-1 items-center justify-end space-x-4">
                    <nav className="flex items-center space-x-1">
                        <Button
                            asChild
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 px-0"
                        >
                            <a
                                href="https://github.com/yuuuiv/auth"
                                target="_blank"
                                rel="noreferrer"
                                aria-label="在 GitHub 查看 Auth 仓库"
                            >
                                <Icons.github className="h-4 w-4" aria-hidden="true" />
                            </a>
                        </Button>
                        <ModeSwitcher />
                    </nav>
                </div>
            </div>
        </header>
    )
}

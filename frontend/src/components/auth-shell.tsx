import type { ReactNode } from "react"
import { X } from "lucide-react"

type AuthShellProps = {
    children: ReactNode
}

export function AuthShell({ children }: AuthShellProps) {
    return (
        <main id="main-content" className="auth-main">
            <section className="auth-account-panel" aria-labelledby="account-title">
                <header className="auth-panel-header">
                    <div>
                        <p className="auth-eyebrow">NeoFantasy Account</p>
                        <h1 id="account-title">用户账户</h1>
                    </div>
                    <a className="auth-panel-close" href="https://live.neofantasy.online/index/" aria-label="关闭并返回 NeoFantasy Live">
                        <X aria-hidden="true" />
                    </a>
                </header>
                <section className="auth-route" aria-label="账号操作">
                    {children}
                </section>
                <footer className="auth-panel-footer">
                    <span>统一账号服务</span>
                    <a href="https://live.neofantasy.online/index/">返回 NeoFantasy Live <span aria-hidden="true">↗</span></a>
                </footer>
            </section>
        </main>
    )
}

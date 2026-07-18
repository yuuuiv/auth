import type { ReactNode } from "react"

type AuthShellProps = {
    children: ReactNode
}

export function AuthShell({ children }: AuthShellProps) {
    return (
        <main id="main-content" className="auth-main">
            <section className="auth-context" aria-labelledby="account-title">
                <p className="auth-eyebrow">NeoFantasy Account</p>
                <h1 id="account-title">账号中心</h1>
                <p className="auth-context-description"><span>登录、注册或重置密码。</span><span>该账号用于访问 NeoFantasy Live。</span></p>

                <dl className="auth-details">
                    <div>
                        <dt>服务</dt>
                        <dd translate="no">NeoFantasy Live</dd>
                    </div>
                    <div>
                        <dt>账号功能</dt>
                        <dd>登录与节目权限同步</dd>
                    </div>
                </dl>

                <a className="auth-site-link" href="https://live.neofantasy.online/index/">
                    返回 Live 站点 <span aria-hidden="true">↗</span>
                </a>
            </section>

            <section className="auth-route" aria-label="账号操作">
                {children}
            </section>
        </main>
    )
}

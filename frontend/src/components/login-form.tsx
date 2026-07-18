import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Icons } from "@/components/icons"
import { Link } from "react-router"
import { UseApiClient } from "@/api"
import { useState } from "react"
import { toast } from "sonner"
import { useNavigate } from "react-router";
import { Eye, EyeClosed, KeyRound, Mail } from "lucide-react"
import { useGlobal } from "@/components/global-provider"
import { LoginType } from "@/type"
import { LoadingSpinner } from "@/components/loading-spinner"

export function LoginForm({
    className,
    ...props
}: React.ComponentPropsWithoutRef<"div">) {
    const { apiFetch } = UseApiClient()
    const navigate = useNavigate()
    const [email, setEmail] = useState<string>("")
    const [password, setPassword] = useState<string>("")
    const [showPassword, setShowPassword] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false)
    const { settings, setJwtSession } = useGlobal();
    const hasOauthProvider = Boolean(
        settings.enabled_github ||
        settings.enabled_google ||
        settings.enabled_ms
    );
    const hasAnyLogin = hasOauthProvider || Boolean(settings.enabled_smtp);

    const onOauthLogin = async (logintype: LoginType) => {
        try {
            const query = new URLSearchParams({
                login_type: logintype,
                redirect_url: `${window.location.origin}/callback/${logintype}`,
            });
            const response = await apiFetch<string>(
                `/api/login?${query.toString()}`,
            );
            if (!response) {
                toast.error(`跳转失败 ${response}`);
                return;
            }
            window.location.href = response;
        } catch (error) {
            toast.error((error as Error).message || "登录失败");
        }
    };

    const emailLogin = async () => {
        if (!email || !password) {
            toast.error("请输入邮箱和密码");
            return;
        }
        setIsSubmitting(true)
        try {
            const res = await apiFetch<{
                access_token: string;
            }>(`/api/session/login`, {
                method: "POST",
                body: JSON.stringify({
                    email: email,
                    password: password,
                })
            });
            if (!res || !res.access_token) {
                toast.error("登录失败");
                return;
            }
            setJwtSession(res.access_token);
            navigate("/user");
        } catch (error) {
            toast.error((error as Error).message || "登录失败");
            console.error((error as Error).message || "登录失败");
        } finally {
            setIsSubmitting(false)
        }
        return;
    };
    return (
        <div className={cn("flex flex-col gap-6", className)} {...props}>
            <Card>
                <CardHeader className="auth-form-header">
                    <div className="auth-form-mark" aria-hidden="true"><KeyRound /></div>
                    <CardTitle>用户登录</CardTitle>
                    <CardDescription>使用统一账户服务访问 NeoFantasy Live</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-6">
                        {settings.error && (
                            <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive" role="status">
                                Auth 后端不可用：{settings.error}
                            </div>
                        )}
                        {!settings.error && !hasAnyLogin && (
                            <div className="rounded-md border bg-muted p-3 text-sm text-muted-foreground" role="status">
                                当前没有启用的登录方式。请检查 Vercel 环境变量：
                                OAuth client ID/secret、enabled_db、auth_jwt_secret、enabled_smtp。
                            </div>
                        )}
                        <div className="oauth-provider-grid">
                            <Button type="button" variant="outline" className="w-full"
                                disabled={!settings.enabled_github}
                                title={settings.enabled_github ? "使用 GitHub 登录" : "GitHub OAuth 尚未配置"}
                                onClick={() => onOauthLogin("github")}>
                                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-black/10 bg-white text-[#181717] shadow-sm">
                                    <Icons.github className="h-4 w-4" aria-hidden="true" />
                                </span>
                                GitHub 登录
                                {!settings.enabled_github && <span className="ml-auto text-xs text-muted-foreground">未配置</span>}
                            </Button>
                            <Button type="button" variant="outline" className="w-full"
                                disabled={!settings.enabled_google}
                                title={settings.enabled_google ? "使用 Google 登录" : "Google OAuth 尚未配置"}
                                onClick={() => onOauthLogin("google")}>
                                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-black/10 bg-white shadow-sm">
                                    <Icons.google className="h-4 w-4" aria-hidden="true" />
                                </span>
                                Google 登录
                                {!settings.enabled_google && <span className="ml-auto text-xs text-muted-foreground">未配置</span>}
                            </Button>
                            {settings.enabled_ms && <Button type="button" variant="outline" className="w-full"
                                onClick={() => onOauthLogin("ms")}>
                                <Icons.microsoft />
                                Microsoft 登录
                            </Button>}
                        </div>
                        {settings.enabled_smtp && (
                            <div className="relative flex items-center gap-3 text-center text-xs text-muted-foreground">
                                <div className="h-px flex-1 bg-border" />
                                <span>或使用邮箱</span>
                                <div className="h-px flex-1 bg-border" />
                            </div>
                        )}
                        {settings.enabled_smtp && (
                            <nav className="auth-segmented" aria-label="选择登录或注册">
                                <Link to="/login" className="is-active" aria-current="page">登录</Link>
                                <Link to="/register">注册</Link>
                            </nav>
                        )}
                        {settings.enabled_smtp &&
                            <form onSubmit={(event) => { event.preventDefault(); void emailLogin() }}>
                                <div className="grid gap-6">
                                    <div className="grid gap-2">
                                        <Label className="sr-only" htmlFor="email">用户邮箱</Label>
                                        <div className="auth-field">
                                            <Mail className="auth-field-icon" aria-hidden="true" />
                                            <Input
                                                className="auth-field-control"
                                                id="email"
                                                name="email"
                                                type="email"
                                                autoComplete="email"
                                                spellCheck={false}
                                                value={email}
                                                onChange={(e) => setEmail(e.target.value)}
                                                placeholder="用户邮箱"
                                            />
                                        </div>
                                    </div>
                                    <div className="grid gap-2">
                                        <Label className="sr-only" htmlFor="password">密码</Label>
                                        <div className="auth-field auth-field-password">
                                            <KeyRound className="auth-field-icon" aria-hidden="true" />
                                            <Input className="auth-field-control" id="password" name="password" type={showPassword ? "text" : "password"}
                                                autoComplete="current-password"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                placeholder="密码"
                                            />
                                            <Button className="auth-password-toggle" type="button" variant="ghost" size="icon" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "隐藏密码" : "显示密码"}>
                                                {showPassword ? <Eye aria-hidden="true" /> : <EyeClosed aria-hidden="true" />}
                                            </Button>
                                        </div>
                                        <Link to="/reset_pass" className="auth-forgot-password">
                                            忘记密码？
                                        </Link>
                                    </div>
                                    <Button type="submit" className="w-full" disabled={isSubmitting}>
                                        {isSubmitting ? <><LoadingSpinner aria-hidden="true" />登录中…</> : "登录"}
                                    </Button>
                                </div>
                                <div className="mt-5 text-center text-sm text-muted-foreground">
                                    还没有账号？{" "}
                                    <Link to="/register" className="underline decoration-primary/40 underline-offset-4">
                                        注册
                                    </Link>
                                </div>
                            </form>
                        }
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

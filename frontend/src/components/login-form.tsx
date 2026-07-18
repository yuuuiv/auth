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
import { Eye, EyeClosed } from "lucide-react"
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
            const callbackOrigin = window.location.hostname === "auth-live-ten.vercel.app"
                ? "https://auth.neofantasy.online"
                : window.location.origin;
            const query = new URLSearchParams({
                login_type: logintype,
                redirect_url: `${callbackOrigin}/callback/${logintype}`,
            });
            if (callbackOrigin !== window.location.origin) {
                window.location.assign(`${callbackOrigin}/api/login/redirect?${query.toString()}`);
                return;
            }
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
                <CardHeader>
                    <CardTitle>登录</CardTitle>
                    <CardDescription>使用第三方账号或邮箱登录。</CardDescription>
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
                                github_client_id、google_client_id、enabled_db、enabled_smtp。
                            </div>
                        )}
                        <div className="flex flex-col gap-4">
                            {settings.enabled_github && <Button type="button" variant="outline" className="w-full"
                                onClick={() => onOauthLogin("github")}>
                                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-black/10 bg-white text-[#181717] shadow-sm">
                                    <Icons.github className="h-4 w-4" aria-hidden="true" />
                                </span>
                                GitHub 登录
                            </Button>}
                            {settings.enabled_google && <Button type="button" variant="outline" className="w-full"
                                onClick={() => onOauthLogin("google")}>
                                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-black/10 bg-white shadow-sm">
                                    <Icons.google className="h-4 w-4" aria-hidden="true" />
                                </span>
                                Google 登录
                            </Button>}
                            {settings.enabled_ms && <Button type="button" variant="outline" className="w-full"
                                onClick={() => onOauthLogin("ms")}>
                                <Icons.microsoft />
                                Microsoft 登录
                            </Button>}
                        </div>
                        {hasOauthProvider && settings.enabled_smtp && (
                            <div className="relative flex items-center gap-3 text-center text-xs text-muted-foreground">
                                <div className="h-px flex-1 bg-border" />
                                <span>或使用邮箱</span>
                                <div className="h-px flex-1 bg-border" />
                            </div>
                        )}
                        {settings.enabled_smtp &&
                            <form onSubmit={(event) => { event.preventDefault(); void emailLogin() }}>
                                <div className="grid gap-6">
                                    <div className="grid gap-2">
                                        <Label htmlFor="email">邮箱</Label>
                                        <Input
                                            id="email"
                                            name="email"
                                            type="email"
                                            autoComplete="email"
                                            spellCheck={false}
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            placeholder="name@example.com"
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <div className="flex items-center">
                                            <Label htmlFor="password" >密码</Label>
                                            <Link to="/reset_pass" className="ml-auto text-sm underline-offset-4 hover:underline">
                                                忘记密码？
                                            </Link>
                                        </div>
                                        <div className="flex w-full items-center space-x-2">
                                            <Input id="password" name="password" type={showPassword ? "text" : "password"}
                                                autoComplete="current-password"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                            />
                                            <Button type="button" variant="ghost" size="icon" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "隐藏密码" : "显示密码"}>
                                                {showPassword ? <Eye aria-hidden="true" /> : <EyeClosed aria-hidden="true" />}
                                            </Button>
                                        </div>

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

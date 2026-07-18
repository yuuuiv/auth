import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    InputOTP,
    InputOTPGroup,
    InputOTPSlot,
} from "@/components/ui/input-otp"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Link, useNavigate } from "react-router"
import { Turnstile } from '@marsidev/react-turnstile'
import { useState } from "react"
import { useTheme } from "@/components/theme-provider"
import { toast } from "sonner"
import { useGlobal } from "@/components/global-provider"
import { UseApiClient } from "@/api"
import { Eye, EyeClosed, KeyRound } from "lucide-react"
import { LoadingSpinner } from "@/components/loading-spinner"

interface EmailVerificationFormProps extends React.ComponentPropsWithoutRef<"div"> {
    mode: "register" | "reset-password"
}

function EmailVerificationForm({
    className,
    mode,
    ...props
}: EmailVerificationFormProps) {
    const isResetPassword = mode === "reset-password"
    const { resolvedTheme } = useTheme()
    const { settings, setJwtSession } = useGlobal()
    const { apiFetch } = UseApiClient()
    const navigate = useNavigate()
    const [token, setToken] = useState<string | null>(null)
    const [email, setEmail] = useState<string>("")
    const [password, setPassword] = useState<string>("")
    const [showPassword, setShowPassword] = useState(false);
    const [code, setCode] = useState<string>("")
    const [verifyCodeTimeout, setVerifyCodeTimeout] = useState<number>(0)
    const [isSendingCode, setIsSendingCode] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)
    if (!settings.enabled_smtp) return null;
    const sendVerificationCode = async () => {
        if (!email) {
            toast.error("请输入邮箱");
            return;
        }
        if (!token && settings.cf_turnstile_site_key) {
            toast.error("请完成人机验证");
            return;
        }
        setIsSendingCode(true)
        try {
            const res = await apiFetch<{
                timeout: number
            }>(`/api/session/verify-code`, {
                method: "POST",
                body: JSON.stringify({
                    email: email,
                    cf_token: token
                })
            });
            if (res && res.timeout) {
                toast.success(`验证码已发送，有效期 ${res.timeout} 秒`);
                setVerifyCodeTimeout(res.timeout);
                const intervalId = setInterval(() => {
                    setVerifyCodeTimeout((prev) => {
                        if (prev <= 1) {
                            clearInterval(intervalId);
                            return 0;
                        }
                        return prev - 1;
                    });
                }, 1000);
            }
        } catch (error) {
            toast.error((error as Error).message || "发送验证码失败");
        } finally {
            setIsSendingCode(false)
        }
    };

    const emailSignup = async () => {
        if (!email || !password || !code) {
            toast.error("请输入邮箱、密码和验证码");
            return;
        }
        setIsSubmitting(true)
        try {
            const res = await apiFetch<{
                access_token: string;
            }>(`/api/session/register`, {
                method: "POST",
                body: JSON.stringify({
                    email: email,
                    password: password,
                    code: code
                })
            });
            if (res && res.access_token) {
                setJwtSession(res.access_token);
                toast.success("注册成功");
                navigate("/user");
            }
        } catch (error) {
            toast.error((error as Error).message || "注册失败");
        } finally {
            setIsSubmitting(false)
        }
    };
    return (
        <div className={cn("flex flex-col gap-6", className)} {...props}>
            <Card>
                <CardHeader className="auth-form-header">
                    <div className="auth-form-mark" aria-hidden="true"><KeyRound /></div>
                    <CardTitle>
                        {isResetPassword ? "重置密码" : "注册"}
                    </CardTitle>
                    <CardDescription>
                        {isResetPassword ? "验证邮箱后设置新密码。" : "通过邮箱验证码创建账号。"}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {!isResetPassword && (
                        <nav className="auth-segmented" aria-label="选择登录或注册">
                            <Link to="/login">登录</Link>
                            <Link to="/register" className="is-active" aria-current="page">注册</Link>
                        </nav>
                    )}
                    <form onSubmit={(event) => { event.preventDefault(); void emailSignup() }}>
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
                                    <Label htmlFor="password">
                                        {isResetPassword ? "新密码" : "密码"}
                                    </Label>
                                </div>
                                <div className="flex w-full items-center space-x-2">
                                    <Input id="password" name="new-password" type={showPassword ? "text" : "password"}
                                        autoComplete="new-password"
                                        minLength={8}
                                        aria-describedby="password-hint"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                    />
                                    <Button type="button" variant="ghost" size="icon" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "隐藏密码" : "显示密码"}>
                                        {showPassword ? <Eye aria-hidden="true" /> : <EyeClosed aria-hidden="true" />}
                                    </Button>
                                </div>
                                <p id="password-hint" className="text-xs text-muted-foreground">至少 8 个字符</p>
                            </div>
                            {settings.cf_turnstile_site_key && <div className="text-center">
                                <Turnstile
                                    siteKey={settings.cf_turnstile_site_key}
                                    options={{
                                        theme: resolvedTheme,
                                        language: 'zh-CN',
                                    }}
                                    onSuccess={setToken} />
                            </div>}
                            <div className="grid gap-2">
                                <Label htmlFor="verification-code">邮箱验证码</Label>
                                <div className="verification-row grid items-center gap-2">
                                    <InputOTP id="verification-code" maxLength={6}
                                        name="verification-code"
                                        autoComplete="one-time-code"
                                        value={code}
                                        onChange={(e) => setCode(e)}
                                    >
                                        <InputOTPGroup>
                                            <InputOTPSlot index={0} />
                                            <InputOTPSlot index={1} />
                                            <InputOTPSlot index={2} />
                                            <InputOTPSlot index={3} />
                                            <InputOTPSlot index={4} />
                                            <InputOTPSlot index={5} />
                                        </InputOTPGroup>
                                    </InputOTP>
                                    <Button type="button" variant="secondary"
                                        disabled={verifyCodeTimeout > 0 || isSendingCode}
                                        onClick={() => sendVerificationCode()}>
                                        {isSendingCode ? <><LoadingSpinner aria-hidden="true" />发送中…</> : verifyCodeTimeout > 0 ? `等待 ${verifyCodeTimeout} 秒` : "发送验证码"}
                                    </Button>
                                </div>
                            </div>
                            <Button type="submit" className="w-full" disabled={isSubmitting}>
                                {isSubmitting ? <><LoadingSpinner aria-hidden="true" />处理中…</> : isResetPassword ? "重置密码" : "注册"}
                            </Button>
                            <Button variant="outline" asChild className="w-full">
                                <Link to="/">返回登录</Link>
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}

type FormContainerProps = React.ComponentPropsWithoutRef<"div">

export function RegisterForm(props: FormContainerProps) {
    return <EmailVerificationForm mode="register" {...props} />
}

export function ResetPasswordForm(props: FormContainerProps) {
    return <EmailVerificationForm mode="reset-password" {...props} />
}

import { cn } from "@/lib/utils";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { UseApiClient } from "@/api";
import { useGlobal } from "@/components/global-provider";

export function Callback({
    className,
    ...props
}: React.ComponentPropsWithoutRef<"div">) {
    const { loginType } = useParams();
    const navigate = useNavigate()
    const { apiFetch } = UseApiClient()
    const { setJwtSession } = useGlobal();
    const [searchParams] = useSearchParams();
    const requestStarted = useRef(false);
    const code = searchParams.get("code") || "";
    const state = searchParams.get("state") || "";
    const providerError = searchParams.get("error_description") || searchParams.get("error") || "";
    const missingCallbackData = !loginType || !code || Boolean(providerError);
    const initialFailureMessage = providerError ? `登录失败：${providerError}` : "登录回调缺少必要参数";
    const [failed, setFailed] = useState(missingCallbackData);
    const [failureMessage, setFailureMessage] = useState(missingCallbackData ? initialFailureMessage : "登录失败，请重试");

    useEffect(() => {
        if (requestStarted.current) return;
        requestStarted.current = true;

        if (missingCallbackData) {
            toast.error(initialFailureMessage);
            return;
        }
        const reqBody = {
            login_type: loginType,
            code,
            state,
            web3_account: searchParams.get("web3_account") || "",
            redirect_url: `${window.location.origin}${window.location.pathname}`
        };
        const loginApiCall = async () => {
            try {
                const response = await apiFetch<{
                    access_token: string;
                    return_to?: string;
                }>(`/api/session/oauth-callback`, {
                    method: "POST",
                    body: JSON.stringify(reqBody)
                });
                if (!response?.access_token) {
                    setFailed(true);
                    setFailureMessage("认证服务没有返回有效会话");
                    toast.error(`登录失败 ${response}`);
                    return;
                }
                setJwtSession(response.access_token);
                if (response.return_to) {
                    window.location.assign(response.return_to);
                } else {
                    navigate("/user", { replace: true });
                }
            } catch (error) {
                setFailed(true);
                const message = (error as Error).message || "登录失败，请重试";
                setFailureMessage(message);
                toast.error(`登录失败 ${message}`);
                return;
            }
        }
        void loginApiCall();
    }, [apiFetch, code, initialFailureMessage, loginType, missingCallbackData, navigate, providerError, searchParams, setJwtSession, state]);

    return (
        <div className={cn("flex flex-col gap-6", className)} {...props}>
            <Card>
                <CardHeader className="text-center">
                    <CardTitle>正在连接账号</CardTitle>
                    <CardDescription>请稍候，我们正在完成安全验证</CardDescription>
                </CardHeader>
                <CardContent>
                    {failed ? (
                        <div className="flex flex-col items-center justify-center gap-2">
                            <p className="text-sm text-red-500">
                                {failureMessage}
                            </p>
                            <Button variant="outline" asChild className="w-full">
                                <Link to="/">返回登录</Link>
                            </Button>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center gap-2">
                            <p className="text-sm text-muted-foreground">
                                正在通过 {loginType} 登录…
                            </p>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}

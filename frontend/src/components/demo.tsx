import { cn } from "@/lib/utils";
import { Link, useSearchParams } from "react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useGlobal } from "@/components/global-provider";
import { toast } from "sonner";
import { UseApiClient } from "@/api";

export function Demo({
    className,
    ...props
}: React.ComponentPropsWithoutRef<"div">) {
    const { apiFetch } = UseApiClient()
    const [URLSearchParams] = useSearchParams();
    const { jwtSession, setJwtSession, appIdSession } = useGlobal();
    const [user, setUser] = useState<Record<string, unknown>>({});
    useEffect(() => {
        const fetchData = async () => {
            const code = URLSearchParams.get("code");
            let activeToken = jwtSession;
            if (code) {
                try {
                    const exchanged = await apiFetch<{ access_token: string }>("/api/session/oauth-exchange", {
                        method: "POST",
                        body: JSON.stringify({ app_id: appIdSession || "demo", code }),
                    });
                    activeToken = exchanged.access_token;
                    setJwtSession(activeToken);
                    window.history.replaceState({}, "", "/user");
                } catch (error) {
                    toast.error((error as Error).message || "登录失败");
                    return;
                }
            }
            if (!activeToken) {
                return;
            }
            try {
                const user_res = await apiFetch<Record<string, unknown>>(`/api/session/me`, {
                    headers: {
                        'Authorization': `Bearer ${activeToken}`,
                        'Content-Type': 'application/json',
                    }
                });
                setUser(user_res);
            } catch (error) {
                toast.error((error as Error).message || "获取用户信息失败");
            }
        }
        fetchData();
    }, []);

    return (
        <div className={cn("flex flex-col gap-6", className)} {...props}>
            <Card>
                <CardHeader className="text-center">
                    <CardTitle>账号信息</CardTitle>
                    <CardDescription>当前 NeoFantasy 身份会话</CardDescription>
                </CardHeader>
                <CardContent>
                    {(user && Object.keys(user).length > 0) ?
                        (
                            <pre className="text-sm whitespace-pre-wrap break-all">{JSON.stringify(user, null, 2)}</pre>
                        ) : (
                            <p className="text-sm">您还没有登录</p>
                        )}
                    <Button variant="outline" asChild className="w-full mt-4">
                        <Link to="/">返回登录</Link>
                    </Button>
                </CardContent>
            </Card>
        </div>
    )
}

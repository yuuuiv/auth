import axios, { AxiosError } from 'axios'
import { useCallback } from 'react'
import { useGlobal } from "@/components/global-provider";

const API_BASE = import.meta.env.VITE_API_BASE || "";

const instance = axios.create({
    baseURL: API_BASE,
    timeout: 10000,
    withCredentials: true,
});

function getErrorDetail(data: unknown): string {
    if (typeof data === "string") return data;
    if (!data || typeof data !== "object") return "请求失败";

    const detail = "detail" in data ? data.detail : data;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        const messages = detail.map((issue) => {
            if (!issue || typeof issue !== "object") return String(issue);
            const location = "loc" in issue && Array.isArray(issue.loc)
                ? issue.loc.filter((item: unknown) => item !== "body").join(".")
                : "";
            const message = "msg" in issue && typeof issue.msg === "string"
                ? issue.msg
                : "请求参数无效";
            return location ? `${location}: ${message}` : message;
        });
        return messages.join("；");
    }

    try {
        return JSON.stringify(detail);
    } catch {
        return "请求失败";
    }
}

export function UseApiClient() {
    const { setIsLoading } = useGlobal();

    const apiFetch = useCallback(async <T>(
        path: string,
        options: {
            method?: string,
            body?: string,
            headers?: unknown
        } = {}
    ): Promise<T> => {
        setIsLoading(true);
        try {
            const response = await instance.request<T>({
                url: path,
                method: options.method || 'GET',
                data: options.body || null,
                headers: options?.headers || {
                    'Content-Type': 'application/json',
                },
            });
            if (response.status >= 300) {
                throw new Error(`[Error]${response.status}: ${response.data}`);
            }
            const data = response.data;
            return data;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                const err = error as AxiosError;
                const status = err.response?.status ?? err.status;
                const detail = getErrorDetail(err.response?.data);
                throw Object.assign(new Error(`[Error]${status ?? "Network"}: ${detail}`), { cause: error });
            } else {
                throw Object.assign(new Error(`[Error]: ${error}`), { cause: error });
            }
        } finally {
            setIsLoading(false);
        }
    }, [setIsLoading])

    return {
        apiFetch
    }
}

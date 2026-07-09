import { BrowserRouter, Route, Routes } from "react-router";
import { Toaster } from "@/components/ui/sonner"

import { LoginForm } from "@/components/login-form"
import { RegisterForm } from "@/components/register-form"
import { SiteHeader } from '@/components/site-header'
import { GlobalProvider } from "@/components/global-provider";
import { useTheme } from "@/components/theme-provider"
import { Callback } from "@/components/callback";
import { Demo } from "@/components/demo";


export default function App() {
  const { theme } = useTheme()
  return (
    <GlobalProvider>
      <div className="bg-muted w-full min-h-screen">
        <Toaster richColors position="top-center" theme={theme} />
        <SiteHeader />
        <div className="flex flex-col items-center justify-center gap-6 p-6 md:p-10">
          <div className="flex w-full max-w-md flex-col gap-6">
            <div className="rounded-2xl border bg-card/80 p-6 text-center shadow-sm backdrop-blur">
              <div className="mx-auto mb-4 flex w-fit gap-1.5">
                <span className="h-2.5 w-2.5 rounded-[3px] bg-primary" />
                <span className="h-2.5 w-2.5 rounded-[3px] bg-primary/70" />
                <span className="h-2.5 w-2.5 rounded-[3px] bg-primary/40" />
              </div>
              <h1 className="text-3xl font-semibold tracking-tight">Temp Mail</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                统一身份登录，保护你的临时邮箱账户
              </p>
            </div>
            <BrowserRouter>
              <Routes>
                <Route index element={<LoginForm />} />
                <Route path="/login" element={<LoginForm />} />
                <Route path="/register" element={<RegisterForm />} />
                <Route path="/reset_pass" element={<RegisterForm ResetPass={true} />} />
                <Route path="/callback/:loginType" element={<Callback />} />
                <Route path="/user" element={<Demo />} />
                <Route path="/demo" element={<Demo />} />
              </Routes>
            </BrowserRouter>
          </div>
        </div>
      </div>
    </GlobalProvider >
  )
}

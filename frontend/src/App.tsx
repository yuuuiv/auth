import { BrowserRouter, Route, Routes } from "react-router";
import { Toaster } from "@/components/ui/sonner"

import { LoginForm } from "@/components/login-form"
import { RegisterForm, ResetPasswordForm } from "@/components/register-form"
import { SiteHeader } from '@/components/site-header'
import { GlobalProvider } from "@/components/global-provider";
import { useTheme } from "@/components/theme-provider"
import { Callback } from "@/components/callback";
import { Demo } from "@/components/demo";
import { AuthShell } from "@/components/auth-shell";


export default function App() {
  const { resolvedTheme } = useTheme()
  return (
    <GlobalProvider>
      <div className="auth-page">
        <Toaster richColors position="top-center" theme={resolvedTheme} />
        <a className="skip-link" href="#main-content">跳到主要内容</a>
        <SiteHeader />
        <BrowserRouter>
          <AuthShell>
              <Routes>
                <Route index element={<LoginForm />} />
                <Route path="/login" element={<LoginForm />} />
                <Route path="/register" element={<RegisterForm />} />
                <Route path="/reset_pass" element={<ResetPasswordForm />} />
                <Route path="/callback/:loginType" element={<Callback />} />
                <Route path="/user" element={<Demo />} />
                <Route path="/demo" element={<Demo />} />
              </Routes>
          </AuthShell>
        </BrowserRouter>
      </div>
    </GlobalProvider >
  )
}

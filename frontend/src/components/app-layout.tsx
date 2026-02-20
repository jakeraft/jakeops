import { Outlet, useLocation } from "react-router"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "./app-sidebar"
import { ThemeSwitch } from "./theme-switch"
import { useTheme } from "@/hooks/use-theme"

const PAGE_TITLES: Record<string, string> = {
  "/sources": "Sources",
  "/deliveries": "Deliveries",
  "/board": "Board",
}

function usePageTitle() {
  const { pathname } = useLocation()
  for (const [prefix, title] of Object.entries(PAGE_TITLES)) {
    if (pathname.startsWith(prefix)) return title
  }
  return "JakeOps"
}

export function AppLayout() {
  const title = usePageTitle()
  const { theme, toggle } = useTheme()
  return (
    <SidebarProvider
      style={{ "--sidebar-width": "12rem" } as React.CSSProperties}
    >
      <AppSidebar />
      <SidebarInset className="min-w-0">
        <header className="flex h-12 items-center justify-between border-b bg-sidebar px-4">
          <span className="text-lg font-semibold">{title}</span>
          <ThemeSwitch checked={theme === "dark"} onCheckedChange={toggle} />
        </header>
        <main className="min-w-0 flex-1 overflow-hidden p-4">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

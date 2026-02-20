import { Outlet, useLocation } from "react-router"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "./app-sidebar"

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
  return (
    <SidebarProvider
      style={{ "--sidebar-width": "12rem" } as React.CSSProperties}
    >
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-10 items-center border-b px-4">
          <span className="text-sm font-medium">{title}</span>
        </header>
        <main className="flex-1 p-4">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

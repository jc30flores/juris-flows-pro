import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppHeader } from "@/components/AppHeader";
import { AppSidebar } from "@/components/AppSidebar";
import Dashboard from "./pages/Dashboard";
import POS from "./pages/POS";
import Clientes from "./pages/Clientes";
import Servicios from "./pages/Servicios";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <SidebarProvider defaultOpen={true}>
            <div className="flex min-h-screen w-full">
              <AppSidebar />
              <div className="flex-1 flex flex-col">
                <AppHeader />
                <main className="flex-1 p-6 overflow-auto">
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/pos" element={<POS />} />
                    <Route path="/ventas" element={<POS />} />
                    <Route path="/servicios" element={<Servicios />} />
                    <Route path="/clientes" element={<Clientes />} />
                    <Route path="/gastos" element={<Dashboard />} />
                    <Route path="/usuarios" element={<Dashboard />} />
                    <Route path="/reportes" element={<Dashboard />} />
                    <Route path="/configuracion" element={<Dashboard />} />
                    <Route path="*" element={<NotFound />} />
                  </Routes>
                </main>
              </div>
            </div>
          </SidebarProvider>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;

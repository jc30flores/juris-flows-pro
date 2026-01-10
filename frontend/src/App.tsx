import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { AppHeader } from "@/components/AppHeader";
import POS from "./pages/POS";
import Clientes from "./pages/Clientes";
import Servicios from "./pages/Servicios";
import Gastos from "./pages/Gastos";
import Usuarios from "./pages/Usuarios";
import NotFound from "./pages/NotFound";
import LoginPage from "./pages/LoginPage";
import { PrivateRoute } from "@/components/PrivateRoute";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { RubroProvider } from "@/contexts/RubroContext";

const queryClient = new QueryClient();

const AppLayout = () => {
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen w-full flex-col overflow-x-hidden">
      {user && <AppHeader />}
      <main className="flex-1 p-3 md:p-6 overflow-auto">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<PrivateRoute />}>
            <Route path="/" element={<Navigate to="/pos" replace />} />
            <Route path="/pos" element={<POS />} />
            <Route path="/servicios" element={<Servicios />} />
            <Route path="/clientes" element={<Clientes />} />
            <Route path="/gastos" element={<Gastos />} />
            <Route path="/usuarios" element={<Usuarios />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <AuthProvider>
            <RubroProvider>
              <AppLayout />
            </RubroProvider>
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;

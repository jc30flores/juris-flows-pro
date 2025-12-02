import { Moon, Sun, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NavLink } from "@/components/NavLink";
import { useTheme } from "next-themes";
import {
  Receipt,
  CreditCard,
  FileText,
  Users,
  UserCog,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const menuItems = [
  { title: "FACTURADOR", url: "/pos", icon: Receipt },
  { title: "SERVICIOS", url: "/servicios", icon: FileText },
  { title: "CLIENTES", url: "/clientes", icon: Users },
  { title: "GASTOS", url: "/gastos", icon: CreditCard },
  { title: "USUARIOS", url: "/usuarios", icon: UserCog },
];

export function AppHeader() {
  const { theme, setTheme } = useTheme();
  const { logout } = useAuth();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="flex h-16 items-center gap-2 md:gap-6 px-3 md:px-6 overflow-x-auto">
        {/* Logo - oculto en móvil */}
        <div className="hidden md:flex items-center gap-2 flex-shrink-0">
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-navy-700 to-navy-500 bg-clip-text text-transparent dark:from-navy-500 dark:to-gold-400 whitespace-nowrap">
            Cuska-OnOffice
          </h1>
        </div>

        {/* Navegación Principal - scroll horizontal en móvil */}
        <nav className="flex items-center justify-center md:justify-start gap-1 flex-1 overflow-x-auto scrollbar-thin">
          {menuItems.map((item) => (
            <NavLink
              key={item.url}
              to={item.url}
              className="flex items-center justify-center gap-2 px-3 md:px-4 py-2 text-sm font-medium text-muted-foreground rounded-md hover:bg-secondary hover:text-foreground transition-smooth whitespace-nowrap flex-shrink-0"
              activeClassName="bg-primary text-primary-foreground hover:bg-primary/90 shadow-md"
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              <span className="hidden md:inline">{item.title}</span>
            </NavLink>
          ))}
        </nav>

        {/* Acciones */}
        <div className="flex items-center gap-1 md:gap-2 flex-shrink-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="transition-smooth flex-shrink-0"
          >
            <Sun className="h-6 w-6 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-6 w-6 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Cambiar tema</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="flex-shrink-0"
            onClick={logout}
          >
            <LogOut className="h-4 w-4" />
            <span className="sr-only">Cerrar sesión</span>
          </Button>
        </div>
      </div>
    </header>
  );
}

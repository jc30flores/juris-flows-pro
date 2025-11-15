import { Moon, Sun, User } from "lucide-react";
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

const menuItems = [
  { title: "POS", url: "/pos", icon: Receipt },
  { title: "Servicios", url: "/servicios", icon: FileText },
  { title: "Clientes", url: "/clientes", icon: Users },
  { title: "Gastos", url: "/gastos", icon: CreditCard },
  { title: "Usuarios", url: "/usuarios", icon: UserCog },
];

export function AppHeader() {
  const { theme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="flex h-16 items-center gap-6 px-6">
        {/* Logo */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-navy-700 to-navy-500 bg-clip-text text-transparent dark:from-navy-500 dark:to-gold-400">
            Cuska-OnOffice
          </h1>
        </div>

        {/* Navegación Principal */}
        <nav className="flex items-center gap-1 flex-1">
          {menuItems.map((item) => (
            <NavLink
              key={item.url}
              to={item.url}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-muted-foreground rounded-md hover:bg-secondary hover:text-foreground transition-smooth"
              activeClassName="bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary"
            >
              <item.icon className="h-4 w-4" />
              <span className="hidden md:inline">{item.title}</span>
            </NavLink>
          ))}
        </nav>

        {/* Acciones */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="transition-smooth"
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Cambiar tema</span>
          </Button>

          <Button variant="ghost" size="icon">
            <User className="h-5 w-5" />
            <span className="sr-only">Usuario</span>
          </Button>
        </div>
      </div>
    </header>
  );
}

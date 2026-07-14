import { Zap } from "lucide-react";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  return (
    <header className="flex items-center justify-between py-6">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Zap className="h-4 w-4 text-white" fill="white" />
        </div>
        <span className="font-display text-lg font-semibold">Fetchly</span>
      </div>
      <ThemeToggle />
    </header>
  );
}

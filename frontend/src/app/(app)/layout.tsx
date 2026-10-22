import { AppShell } from "@/components/layout/AppShell";
import { ConfigProvider } from "@/providers/ConfigProvider";
import { SearchSessionProvider } from "@/providers/SearchSessionProvider";

export default function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <ConfigProvider>
      <SearchSessionProvider>
        <AppShell>{children}</AppShell>
      </SearchSessionProvider>
    </ConfigProvider>
  );
}

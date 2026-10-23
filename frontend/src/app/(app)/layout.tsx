import { AppShell } from "@/components/layout/AppShell";
import { AuthProvider } from "@/providers/AuthProvider";
import { ConfigProvider } from "@/providers/ConfigProvider";
import { SearchSessionProvider } from "@/providers/SearchSessionProvider";

export default function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <AuthProvider>
      <ConfigProvider>
        <SearchSessionProvider>
          <AppShell>{children}</AppShell>
        </SearchSessionProvider>
      </ConfigProvider>
    </AuthProvider>
  );
}

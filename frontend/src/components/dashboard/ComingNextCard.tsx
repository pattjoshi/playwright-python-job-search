import Link from "next/link";

import { NAV_ITEMS } from "@/components/layout/nav";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** What's coming in the next phases, linking to each page's preview. */
export function ComingNextCard() {
  const soon = NAV_ITEMS.filter((item) => item.soon);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Coming next</CardTitle>
        <CardDescription>New pages arriving in the next phases.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-2">
        {soon.map(({ href, label, description, icon: Icon }) => (
          <Link key={href} href={href} className="flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-accent/50">
            <Icon className="size-4 shrink-0 text-primary" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{label}</p>
              <p className="truncate text-xs text-muted-foreground">{description}</p>
            </div>
            <Badge variant="secondary">Soon</Badge>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}

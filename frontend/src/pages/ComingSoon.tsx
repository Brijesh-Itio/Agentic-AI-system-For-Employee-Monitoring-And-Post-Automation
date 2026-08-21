import { type LucideIcon, Construction } from "lucide-react";
import PageMeta from "../components/common/PageMeta";
import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";

interface ComingSoonProps {
  title: string;
  moduleLabel: string;
  description: string;
  icon?: LucideIcon;
}

export default function ComingSoon({ title, moduleLabel, description, icon: Icon = Construction }: ComingSoonProps) {
  return (
    <>
      <PageMeta title={`${title} | WorkPulse AI`} description={description} />
      <div className="flex min-h-[70vh] items-center justify-center">
        <Card className="w-full max-w-md text-center">
          <CardContent className="flex flex-col items-center gap-4 pt-10 pb-10">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400">
              <Icon className="h-7 w-7" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
            </div>
            <Badge variant="outline">{moduleLabel} — not built yet</Badge>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

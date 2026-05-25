import { LucideIcon } from "lucide-react";

type Props = {
  label: string;
  value: string;
  icon: LucideIcon;
  iconBg: string;
};

export function MetricCard({ label, value, icon: Icon, iconBg }: Props) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className={`rounded-lg p-3 ${iconBg}`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  );
}

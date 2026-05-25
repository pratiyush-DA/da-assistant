import Link from "next/link";
import { LucideIcon } from "lucide-react";

type Props = {
  title: string;
  description: string;
  href?: string;
  icon: LucideIcon;
  iconColor: string;
  disabled?: boolean;
};

export function FeatureTile({
  title,
  description,
  href,
  icon: Icon,
  iconColor,
  disabled,
}: Props) {
  const inner = (
    <div
      className={`flex flex-col items-center rounded-xl border border-gray-100 bg-white p-8 shadow-sm transition ${
        disabled ? "cursor-not-allowed opacity-60" : "hover:shadow-md"
      }`}
    >
      <div className={`mb-4 rounded-full p-4 ${iconColor}`}>
        <Icon className="h-8 w-8 text-white" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 text-center text-sm text-gray-500">{description}</p>
      {disabled && (
        <span className="mt-3 rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-500">
          Phase 2
        </span>
      )}
    </div>
  );

  if (disabled || !href) return inner;
  return <Link href={href}>{inner}</Link>;
}

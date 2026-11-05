import type { ButtonHTMLAttributes, ReactNode } from "react";
import Icon, { type IconName } from "@/components/ui/Icon";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg" | "xl";

const VARIANT: Record<Variant, string> = { primary: "btn-gold", secondary: "btn", ghost: "btn-ghost", danger: "btn-danger" };
const SIZE: Record<Size, string> = { sm: "btn-sm", md: "", lg: "btn-lg", xl: "btn-xl" };

/** Class names for a link that looks like a button (Next <Link> or <a>). */
export function buttonClass(variant: Variant = "secondary", size: Size = "md", extra = ""): string {
  return [VARIANT[variant], SIZE[size], extra].filter(Boolean).join(" ");
}

/**
 * Button with the design system's states: hover, focus-visible ring, pressed (gold buttons sink on their edge),
 * disabled, and loading (a spinner in place of the icon, the label stays so nothing jumps and the meaning stays).
 */
export default function Button({
  variant = "secondary",
  size = "md",
  icon,
  loading = false,
  className = "",
  children,
  disabled,
  type = "button",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  icon?: IconName;
  loading?: boolean;
  children: ReactNode;
}) {
  const ic = size === "xl" || size === "lg" ? "h-6 w-6" : size === "sm" ? "h-4 w-4" : "h-5 w-5";
  return (
    <button
      type={type}
      className={buttonClass(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className="spinner" aria-hidden="true" /> : icon ? <Icon name={icon} className={ic} /> : null}
      {children}
    </button>
  );
}

import { Moon, Sun } from "lucide-react"
import { Switch as SwitchPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"

export function ThemeSwitch({
  checked,
  onCheckedChange,
}: {
  checked: boolean
  onCheckedChange: () => void
}) {
  return (
    <SwitchPrimitive.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      aria-label="Toggle theme"
      className={cn(
        "peer inline-flex h-5 w-9 shrink-0 items-center rounded-full border border-transparent shadow-xs transition-colors outline-none",
        "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]",
        "data-[state=checked]:bg-primary data-[state=unchecked]:bg-input dark:data-[state=unchecked]:bg-input/80"
      )}
    >
      <SwitchPrimitive.Thumb
        className={cn(
          "pointer-events-none flex items-center justify-center rounded-full ring-0 transition-transform size-4",
          "bg-background dark:data-[state=unchecked]:bg-foreground dark:data-[state=checked]:bg-primary-foreground",
          "data-[state=checked]:translate-x-[calc(100%+2px)] data-[state=unchecked]:translate-x-0.5"
        )}
      >
        {checked ? (
          <Moon className="size-2.5" />
        ) : (
          <Sun className="size-2.5 text-foreground" />
        )}
      </SwitchPrimitive.Thumb>
    </SwitchPrimitive.Root>
  )
}

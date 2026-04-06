"use client";

export function JsonBlock({
  value,
  className = "",
}: {
  value: unknown;
  className?: string;
}) {
  return (
    <pre
      className={`max-h-[28rem] overflow-auto rounded-md bg-muted p-3 text-xs font-mono leading-relaxed ${className}`}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

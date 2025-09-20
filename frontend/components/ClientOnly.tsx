"use client";

import { useEffect, useState } from "react";

interface ClientOnlyProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  className?: string;
}

export default function ClientOnly({
  children,
  fallback = (
    <div className="animate-pulse bg-gray-200 rounded h-4 w-full">
      <div className="flex items-center justify-center h-full">
        <div className="text-xs text-gray-500">Chargement...</div>
      </div>
    </div>
  ),
  className,
}: ClientOnlyProps) {
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []);

  if (!hasMounted) {
    return <div className={className}>{fallback}</div>;
  }

  return <div className={className}>{children}</div>;
}

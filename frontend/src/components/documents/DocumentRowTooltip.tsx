"use client";

import { ReactNode, useState } from "react";
import { formatBytes } from "@/lib/format";

type Props = {
  filename: string;
  chunkCount: number;
  fileSizeBytes: number | null;
  children: ReactNode;
};

export function DocumentRowTooltip({
  filename,
  chunkCount,
  fileSizeBytes,
  children,
}: Props) {
  const [show, setShow] = useState(false);

  return (
    <div
      className="relative min-w-0 flex-1"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div
          role="tooltip"
          className="absolute left-0 top-full z-30 mt-1 w-max max-w-xs rounded-lg border border-gray-200 bg-gray-900 px-3 py-2 text-xs text-white shadow-lg"
        >
          <p className="font-medium break-all">{filename}</p>
          <p className="mt-1 text-gray-300">{chunkCount} chunks</p>
          <p className="text-gray-300">Size: {formatBytes(fileSizeBytes)}</p>
        </div>
      )}
    </div>
  );
}

// Vendored from canvas-ui (MIT): https://github.com/DavidHDev/canvas-ui
// Registry item @canvas-ui/dithered-object-react. Do not hand-edit;
// re-fetch from upstream to update.
"use client";

import { useEffect, useRef, useState } from "react";

import {
  createDitheredObject,
  type DitheredObjectInstance,
  type DitheredObjectOptions,
} from "./DitheredObjectVanilla";

export interface DitheredObjectProps extends DitheredObjectOptions {
  className?: string;
  style?: React.CSSProperties;
}

export function DitheredObject({
  className,
  style,
  ...options
}: DitheredObjectProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const instanceRef = useRef<DitheredObjectInstance | null>(null);
  const [initialOptions] = useState(options);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    instanceRef.current = createDitheredObject({ canvas }, initialOptions);
    return () => {
      instanceRef.current?.destroy();
      instanceRef.current = null;
    };
  }, [initialOptions]);

  useEffect(() => {
    instanceRef.current?.setOptions(options);
  });

  return (
    <div className={className} style={{ position: "relative", ...style }}>
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          display: "block",
          touchAction: "none",
        }}
      />
    </div>
  );
}

export type { DitheredObjectInstance, DitheredObjectOptions };

export default DitheredObject;

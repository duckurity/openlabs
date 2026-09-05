'use client';

import * as React from 'react';
import * as THREE from 'three';

// Brand: Ember wave over Canvas ground. Hex mirrors the theming
// tokens var(--action-500) and the Canvas surface. The engine needs hex.
const EMBER = '#FF3616';
const CANVAS = '#1C1916';

const VERT = `
varying vec2 vUv;
void main() {
  vUv = position.xy * 0.5 + 0.5;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}`;

const FRAG = `
precision highp float;
varying vec2 vUv;
uniform vec2 uResolution;
uniform float uTime;
uniform float uSeed;
uniform float uWaveSpeed;
uniform float uWaveFrequency;
uniform float uWaveAmplitude;
uniform vec3 uWaveColor;
uniform vec3 uBackgroundColor;
uniform float uColorNum;
uniform float uPixelSize;

vec3 toSrgb(vec3 c) {
  c = clamp(c, 0.0, 1.0);
  return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
vec2 fade(vec2 t) { return t * t * t * (t * (t * 6.0 - 15.0) + 10.0); }

float cnoise(vec2 P) {
  vec4 Pi = floor(P.xyxy) + vec4(0.0, 0.0, 1.0, 1.0);
  vec4 Pf = fract(P.xyxy) - vec4(0.0, 0.0, 1.0, 1.0);
  Pi = mod289(Pi);
  vec4 ix = Pi.xzxz;
  vec4 iy = Pi.yyww;
  vec4 fx = Pf.xzxz;
  vec4 fy = Pf.yyww;
  vec4 i = permute(permute(ix) + iy);
  vec4 gx = fract(i * (1.0 / 41.0)) * 2.0 - 1.0;
  vec4 gy = abs(gx) - 0.5;
  vec4 tx = floor(gx + 0.5);
  gx = gx - tx;
  vec2 g00 = vec2(gx.x, gy.x);
  vec2 g10 = vec2(gx.y, gy.y);
  vec2 g01 = vec2(gx.z, gy.z);
  vec2 g11 = vec2(gx.w, gy.w);
  vec4 norm = taylorInvSqrt(vec4(dot(g00, g00), dot(g01, g01), dot(g10, g10), dot(g11, g11)));
  g00 *= norm.x; g01 *= norm.y; g10 *= norm.z; g11 *= norm.w;
  float n00 = dot(g00, vec2(fx.x, fy.x));
  float n10 = dot(g10, vec2(fx.y, fy.y));
  float n01 = dot(g01, vec2(fx.z, fy.z));
  float n11 = dot(g11, vec2(fx.w, fy.w));
  vec2 fade_xy = fade(Pf.xy);
  vec2 n_x = mix(vec2(n00, n01), vec2(n10, n11), fade_xy.x);
  return 2.3 * mix(n_x.x, n_x.y, fade_xy.y);
}

float fbm(vec2 p) {
  float value = 0.0;
  float amp = 1.0;
  float freq = uWaveFrequency;
  for (int i = 0; i < 4; i++) {
    value += amp * abs(cnoise(p));
    p *= freq;
    amp *= uWaveAmplitude;
  }
  return value;
}

float pattern(vec2 p) {
  vec2 seedOff = vec2(fract(uSeed * 0.371), fract(uSeed * 0.737)) * 4.0;
  vec2 p2 = p + seedOff - uTime * uWaveSpeed;
  return fbm(p + seedOff + fbm(p2));
}

// Canonical 8x8 Bayer via recursion. Matches the reference matrix
// without dynamic array indexing.
float bayer2(vec2 a) {
  a = floor(a);
  return fract(a.x / 2.0 + a.y * a.y * 0.75);
}
float bayer4(vec2 a) { return bayer2(0.5 * a) * 0.25 + bayer2(a); }
float bayer8(vec2 a) { return bayer4(0.5 * a) * 0.25 + bayer2(a); }

void main() {
  vec2 fragCoord = vUv * uResolution;
  vec2 cellId = floor(fragCoord / uPixelSize);
  vec2 uv = ((cellId + 0.5) * uPixelSize) / uResolution;
  vec2 p = uv - 0.5;
  p.x *= uResolution.x / uResolution.y;
  float f = pattern(p);
  vec3 col = mix(uBackgroundColor, uWaveColor, clamp(f, 0.0, 1.0));
  float threshold = bayer8(cellId) - 0.25;
  float stepSize = 1.0 / (uColorNum - 1.0);
  col += threshold * stepSize;
  float luminance = dot(col, vec3(0.2126, 0.7152, 0.0722));
  float bias = mix(0.2, 0.0, smoothstep(0.45, 0.8, luminance));
  col = clamp(col - bias, 0.0, 1.0);
  col = floor(col * (uColorNum - 1.0) + 0.5) / (uColorNum - 1.0);
  gl_FragColor = vec4(toSrgb(col), 1.0);
}`;

export interface DitherWavesProps {
  waveColor?: string;
  backgroundColor?: string;
  waveSpeed?: number;
  waveFrequency?: number;
  waveAmplitude?: number;
  colorNum?: number;
  pixelSize?: number;
  /** 0..1. Offsets the field so each surface gets unique art. */
  seed?: number;
  /** Freeze on the first frame. Reduced motion forces this on. */
  disableAnimation?: boolean;
  className?: string;
  style?: React.CSSProperties;
  onError?: (error: unknown) => void;
}

/**
 * Fullscreen Ember wave field with Bayer dither. Renders opaque and
 * fills its host. Freezes on reduced motion. Stops offscreen.
 */
export function DitherWaves({
  waveColor = EMBER,
  backgroundColor = CANVAS,
  waveSpeed = 0.05,
  waveFrequency = 3,
  waveAmplitude = 0.3,
  colorNum = 4,
  pixelSize = 2,
  seed = 0,
  disableAnimation = false,
  className,
  style,
  onError,
}: DitherWavesProps) {
  const hostRef = React.useRef<HTMLDivElement>(null);
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const errorRef = React.useRef(onError);
  errorRef.current = onError;
  const [initial] = React.useState(() => ({
    waveColor,
    backgroundColor,
    waveSpeed,
    waveFrequency,
    waveAmplitude,
    colorNum,
    pixelSize,
    seed,
    disableAnimation,
  }));

  React.useEffect(() => {
    const host = hostRef.current;
    const canvas = canvasRef.current;
    if (!host || !canvas) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: false,
        alpha: false,
        powerPreference: 'low-power',
      });
    } catch (error) {
      errorRef.current?.(error);
      return;
    }
    renderer.setPixelRatio(1);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      'position',
      new THREE.BufferAttribute(
        new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]),
        3
      )
    );
    const material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      uniforms: {
        uResolution: { value: new THREE.Vector2(1, 1) },
        uTime: { value: 0 },
        uSeed: { value: initial.seed },
        uWaveSpeed: { value: initial.waveSpeed },
        uWaveFrequency: { value: initial.waveFrequency },
        uWaveAmplitude: { value: initial.waveAmplitude },
        uWaveColor: { value: new THREE.Color(initial.waveColor) },
        uBackgroundColor: {
          value: new THREE.Color(initial.backgroundColor),
        },
        uColorNum: { value: initial.colorNum },
        uPixelSize: { value: initial.pixelSize },
      },
      depthTest: false,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.frustumCulled = false;
    scene.add(mesh);

    const resize = () => {
      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);
      renderer.setSize(width, height, false);
      const resolution = material.uniforms.uResolution
        .value as THREE.Vector2;
      resolution.set(width, height);
    };
    resize();

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    let disposed = false;
    let running = false;
    const clock = new THREE.Clock();

    const renderAt = (time: number) => {
      (material.uniforms.uTime.value as number) = time;
      renderer.render(scene, camera);
    };

    const start = () => {
      if (running || disposed) return;
      running = true;
      clock.start();
      renderer.setAnimationLoop(() => {
        renderAt(clock.getElapsedTime());
      });
    };
    const stop = () => {
      if (!running) return;
      running = false;
      renderer.setAnimationLoop(null);
    };
    const renderStatic = () => {
      stop();
      if (!disposed) renderAt(0);
    };

    const frozen = () =>
      initial.disableAnimation || motionQuery.matches;
    const onMotionChange = () => {
      if (frozen()) renderStatic();
      else if (inView) start();
    };
    motionQuery.addEventListener('change', onMotionChange);

    let inView = true;
    const viewObserver =
      typeof IntersectionObserver !== 'undefined'
        ? new IntersectionObserver((entries) => {
            inView = entries[entries.length - 1]?.isIntersecting ?? true;
            if (!inView) {
              stop();
            } else if (!frozen()) {
              start();
            }
          })
        : null;
    viewObserver?.observe(host);

    const sizeObserver = new ResizeObserver(resize);
    sizeObserver.observe(host);

    if (frozen()) renderStatic();
    else start();

    return () => {
      disposed = true;
      stop();
      sizeObserver.disconnect();
      viewObserver?.disconnect();
      motionQuery.removeEventListener('change', onMotionChange);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, [initial]);

  return (
    <div ref={hostRef} className={className} style={style}>
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          display: 'block',
        }}
      />
    </div>
  );
}

export default DitherWaves;

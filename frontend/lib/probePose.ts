import { Euler, Quaternion, Vector3 } from "three";
import syntheticHeadSurface from "./generated/syntheticHeadSurface.json";

const HEAD_GROUP_EULER = new Euler(0.2, -0.35, 0, "XYZ");
const PROBE_LOCAL_TRANSDUCER_CENTER = new Vector3(0, -0.625, 0);
const TRANSDUCER_RADIUS = 0.12;
const PROBE_TILT_RAD = 0.52;

type SurfaceSample = {
  point: Vector3;
  normal: Vector3;
};

const SURFACE_SAMPLES: SurfaceSample[] = syntheticHeadSurface.samples.map((sample) => ({
  point: new Vector3(sample.point[0], sample.point[1], sample.point[2]).applyEuler(HEAD_GROUP_EULER),
  normal: new Vector3(sample.normal[0], sample.normal[1], sample.normal[2])
    .applyEuler(HEAD_GROUP_EULER)
    .normalize(),
}));

const INTERACTIVE_SURFACE_SAMPLES = SURFACE_SAMPLES.filter(
  (sample) => sample.point.z > -0.25 && sample.normal.z > -0.05,
);

const SURFACE_SAMPLE_BOUNDS = INTERACTIVE_SURFACE_SAMPLES.reduce(
  (bounds, sample) => ({
    minX: Math.min(bounds.minX, sample.point.x),
    maxX: Math.max(bounds.maxX, sample.point.x),
    minY: Math.min(bounds.minY, sample.point.y),
    maxY: Math.max(bounds.maxY, sample.point.y),
  }),
  {
    minX: Number.POSITIVE_INFINITY,
    maxX: Number.NEGATIVE_INFINITY,
    minY: Number.POSITIVE_INFINITY,
    maxY: Number.NEGATIVE_INFINITY,
  },
);

export type ProbePose = {
  probePosition: [number, number, number];
  probeRotation: [number, number, number];
  contactPoint: [number, number, number];
  outwardNormal: [number, number, number];
  probeAxis: [number, number, number];
};

function clampControl(value: number): number {
  return Math.min(100, Math.max(0, value));
}

function selectSurfaceSample(probeX: number, probeY: number): SurfaceSample {
  const normalizedX = clampControl(probeX) / 100;
  const normalizedY = clampControl(probeY) / 100;
  const targetX = SURFACE_SAMPLE_BOUNDS.minX
    + normalizedX * (SURFACE_SAMPLE_BOUNDS.maxX - SURFACE_SAMPLE_BOUNDS.minX);
  const targetY = SURFACE_SAMPLE_BOUNDS.maxY
    - normalizedY * (SURFACE_SAMPLE_BOUNDS.maxY - SURFACE_SAMPLE_BOUNDS.minY);

  let bestSample = INTERACTIVE_SURFACE_SAMPLES[0];
  let bestScore = Number.POSITIVE_INFINITY;

  for (const sample of INTERACTIVE_SURFACE_SAMPLES) {
    const dx = sample.point.x - targetX;
    const dy = sample.point.y - targetY;
    const score = (dx * dx) + (dy * dy) - (sample.point.z * 0.02);
    if (score < bestScore) {
      bestScore = score;
      bestSample = sample;
    }
  }

  return bestSample;
}

export function computeProbePose(
  probeX: number,
  probeY: number,
  probeRotation: number,
): ProbePose {
  const surfaceSample = selectSurfaceSample(probeX, probeY);
  const contactPointWorld = surfaceSample.point.clone();
  const outwardNormalWorld = surfaceSample.normal.clone().normalize();

  const tangentReference =
    Math.abs(outwardNormalWorld.z) > 0.92
      ? new Vector3(1, 0, 0)
      : new Vector3(0, 0, 1);
  const tangentU = new Vector3().crossVectors(tangentReference, outwardNormalWorld).normalize();
  const tangentV = new Vector3().crossVectors(outwardNormalWorld, tangentU).normalize();
  const rotationRad = (probeRotation * Math.PI) / 180;
  const tangentDirection = tangentU
    .clone()
    .multiplyScalar(Math.cos(rotationRad))
    .add(tangentV.clone().multiplyScalar(Math.sin(rotationRad)));
  const probeAxisWorld = outwardNormalWorld
    .clone()
    .multiplyScalar(Math.cos(PROBE_TILT_RAD))
    .add(tangentDirection.multiplyScalar(Math.sin(PROBE_TILT_RAD)))
    .normalize();

  const probeQuaternion = new Quaternion().setFromUnitVectors(
    new Vector3(0, 1, 0),
    probeAxisWorld,
  );

  const transducerCenterWorld = contactPointWorld
    .clone()
    .add(outwardNormalWorld.clone().multiplyScalar(TRANSDUCER_RADIUS));
  const probeOriginWorld = transducerCenterWorld.sub(
    PROBE_LOCAL_TRANSDUCER_CENTER.clone().applyQuaternion(probeQuaternion),
  );
  const probeEuler = new Euler().setFromQuaternion(probeQuaternion, "XYZ");

  return {
    probePosition: [probeOriginWorld.x, probeOriginWorld.y, probeOriginWorld.z],
    probeRotation: [probeEuler.x, probeEuler.y, probeEuler.z],
    contactPoint: [contactPointWorld.x, contactPointWorld.y, contactPointWorld.z],
    outwardNormal: [outwardNormalWorld.x, outwardNormalWorld.y, outwardNormalWorld.z],
    probeAxis: [probeAxisWorld.x, probeAxisWorld.y, probeAxisWorld.z],
  };
}

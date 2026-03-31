"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas, ThreeEvent, useLoader } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Mesh } from "three";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";

import { AnatomyModel, fallbackAnatomyModel } from "../lib/anatomy";

type ViewportSceneProps = {
  probeX: number;
  probeY: number;
  probeRotation: number;
  focalDepth: number;
  intensity: number;
  onProbePoseChange: (pose: { x: number; y: number }) => void;
};

function HeadModel({ model }: { model: AnatomyModel }) {
  return (
    <group rotation={[0.2, -0.35, 0]}>
      {model.layers.map((layer) => (
        <mesh
          key={layer.id}
          position={layer.position}
          scale={layer.scale}
          castShadow
          receiveShadow
        >
          <sphereGeometry args={[1, 52, 52]} />
          <meshStandardMaterial
            color={layer.color}
            transparent={layer.opacity < 1}
            opacity={layer.opacity}
            roughness={0.5}
            metalness={0.02}
          />
        </mesh>
      ))}
      <mesh position={[0.54, -0.06, 1.06]} castShadow>
        <sphereGeometry args={[0.4, 36, 36]} />
        <meshStandardMaterial color="#e6ddd1" roughness={0.62} metalness={0.02} />
      </mesh>
      {model.landmarks.map((landmark) => (
        <mesh key={landmark.id} position={landmark.position} castShadow>
          <sphereGeometry args={[0.05, 16, 16]} />
          <meshStandardMaterial color="#bf623f" emissive="#a14f30" emissiveIntensity={0.35} />
        </mesh>
      ))}
      {(model.meshes ?? []).map((mesh) => (
        <ImportedMesh
          key={mesh.id}
          url={mesh.url}
          color={mesh.color}
          opacity={mesh.opacity}
          position={mesh.position}
          scale={mesh.scale}
          rotationDeg={mesh.rotationDeg}
        />
      ))}
    </group>
  );
}

function ImportedMesh({
  url,
  color,
  opacity = 0.95,
  position = [0, 0, 0],
  scale = [1, 1, 1],
  rotationDeg = [0, 0, 0],
}: {
  url: string;
  color: string;
  opacity?: number;
  position?: [number, number, number];
  scale?: [number, number, number];
  rotationDeg?: [number, number, number];
}) {
  const object = useLoader(OBJLoader, url);
  const rotation = rotationDeg.map((value) => (value * Math.PI) / 180) as [
    number,
    number,
    number,
  ];

  const cloned = useMemo(() => {
    const next = object.clone();
    next.traverse((child) => {
      if (child instanceof Mesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        if (Array.isArray(child.material)) {
          child.material = child.material.map((material) => {
            const nextMaterial = material.clone();
            nextMaterial.color.set(color);
            nextMaterial.transparent = opacity < 1;
            nextMaterial.opacity = opacity;
            return nextMaterial;
          });
        } else {
          child.material = child.material.clone();
          child.material.color.set(color);
          child.material.transparent = opacity < 1;
          child.material.opacity = opacity;
        }
      }
    });
    return next;
  }, [object, color, opacity]);

  return (
    <primitive
      object={cloned}
      position={position}
      scale={scale}
      rotation={rotation}
    />
  );
}

function ProbeModel({
  probeX,
  probeY,
  probeRotation,
}: Pick<ViewportSceneProps, "probeX" | "probeY" | "probeRotation">) {
  const x = ((probeX - 50) / 50) * 1.3;
  const y = ((50 - probeY) / 50) * 1.1 + 1.25;
  const zRotation = (probeRotation * Math.PI) / 180;

  return (
    <group position={[x, y, 0.85]} rotation={[0.55, 0.1, zRotation]}>
      <mesh castShadow>
        <capsuleGeometry args={[0.13, 1.25, 8, 24]} />
        <meshStandardMaterial color="#50555d" roughness={0.34} metalness={0.48} />
      </mesh>
      <mesh position={[0, -0.625, 0]} castShadow>
        <sphereGeometry args={[0.12, 20, 20]} />
        <meshStandardMaterial color="#71c1ce" emissive="#3b7e86" emissiveIntensity={0.4} />
      </mesh>
    </group>
  );
}

function ProbeDragSurface({
  onProbePoseChange,
  probeRotation,
}: Pick<ViewportSceneProps, "onProbePoseChange" | "probeRotation">) {
  const [dragging, setDragging] = useState(false);

  function updateFromPoint(event: ThreeEvent<PointerEvent>) {
    const nextX = Math.min(100, Math.max(0, ((event.point.x + 2.2) / 4.4) * 100));
    const nextY = Math.min(100, Math.max(0, 50 - ((event.point.y - 0.3) / 2.6) * 50));
    const [constrainedX, constrainedY] = constrainProbePosition(nextX, nextY);
    onProbePoseChange({
      x: Number(constrainedX.toFixed(1)),
      y: Number(constrainedY.toFixed(1)),
    });
  }

  function constrainProbePosition(probeX: number, probeY: number): [number, number] {
    // Constrain to the visible outer scalp shell (fallback layer), not the inner sphere.
    const HEAD_LOCAL_CENTER: [number, number, number] = [0, -0.08, 0];
    const HEAD_GROUP_ROT_X = 0.2;
    const HEAD_GROUP_ROT_Y = -0.35;
    const HEAD_GROUP_ROT_Z = 0;
    const HEAD_RADIUS = 1.66;
    const PROBE_Z = 0.85;
    const PROBE_ROT_X = 0.55;
    const PROBE_ROT_Y = 0.1;
    const PROBE_ROT_Z = (probeRotation * Math.PI) / 180;

    function rotatePointXYZ(
      point: [number, number, number],
      rx: number,
      ry: number,
      rz: number,
    ): [number, number, number] {
      const [x0, y0, z0] = point;
      const cx = Math.cos(rx);
      const sx = Math.sin(rx);
      const cy = Math.cos(ry);
      const sy = Math.sin(ry);
      const cz = Math.cos(rz);
      const sz = Math.sin(rz);

      const x1 = x0;
      const y1 = y0 * cx - z0 * sx;
      const z1 = y0 * sx + z0 * cx;

      const x2 = x1 * cy + z1 * sy;
      const y2 = y1;
      const z2 = -x1 * sy + z1 * cy;

      const x3 = x2 * cz - y2 * sz;
      const y3 = x2 * sz + y2 * cz;
      const z3 = z2;

      return [x3, y3, z3];
    }

    const HEAD_CENTER = rotatePointXYZ(
      HEAD_LOCAL_CENTER,
      HEAD_GROUP_ROT_X,
      HEAD_GROUP_ROT_Y,
      HEAD_GROUP_ROT_Z,
    );

    const probeStartY = -0.625;
    const probeEndY = 0.755;
    const probeSampleCount = 14;
    const probeStep = (probeEndY - probeStartY) / (probeSampleCount - 1);
    const localCollisionPoints: Array<{ p: [number, number, number]; r: number }> = [
      { p: [0, -0.625, 0], r: 0.12 },
      ...Array.from({ length: probeSampleCount }, (_, i) => ({
        p: [0, probeStartY + (i * probeStep), 0] as [number, number, number],
        r: 0.13,
      })),
    ];

    let probeX3d = ((probeX - 50) / 50) * 1.3;
    let probeY3d = ((50 - probeY) / 50) * 1.1 + 1.25;

    for (let i = 0; i < 24; i += 1) {
      let correctionX = 0;
      let correctionY = 0;
      let violated = false;

      for (const sample of localCollisionPoints) {
        const rotated = rotatePointXYZ(sample.p, PROBE_ROT_X, PROBE_ROT_Y, PROBE_ROT_Z);
        const wx = probeX3d + rotated[0];
        const wy = probeY3d + rotated[1];
        const wz = PROBE_Z + rotated[2];

        const dx = wx - HEAD_CENTER[0];
        const dy = wy - HEAD_CENTER[1];
        const dz = wz - HEAD_CENTER[2];
        const minDistance = HEAD_RADIUS + sample.r + 0.01;

        // We can only move the probe in x/y. Enforce the required x/y offset
        // for each sample point given its z-separation from head center.
        if (Math.abs(dz) >= minDistance) {
          continue;
        }

        const requiredXY = Math.sqrt((minDistance * minDistance) - (dz * dz));
        const dxy = Math.sqrt(dx * dx + dy * dy);

        if (dxy < requiredXY) {
          violated = true;
          const safeXY = Math.max(dxy, 1e-6);
          const penetrationXY = requiredXY - safeXY;
          const nx = dx / safeXY;
          const ny = dy / safeXY;
          
          // If exactly centered in x/y, use a stable outward direction.
          if (safeXY <= 1e-6) {
            correctionX += penetrationXY;
            continue;
          }

          correctionX += nx * penetrationXY;
          correctionY += ny * penetrationXY;
        }

        const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (distance < minDistance) {
          violated = true;
          const safeDistance = Math.max(distance, 1e-6);
          const penetration = minDistance - safeDistance;
          const nx3 = dx / safeDistance;
          const ny3 = dy / safeDistance;
          correctionX += nx3 * penetration * 0.25;
          correctionY += ny3 * penetration * 0.25;
        }
      }

      if (!violated) {
        break;
      }

      probeX3d += correctionX;
      probeY3d += correctionY;
    }

    const nextProbeX = ((probeX3d / 1.3) * 50) + 50;
    const nextProbeY = 50 - ((probeY3d - 1.25) / 1.1) * 50;

    return [
      Math.min(100, Math.max(0, nextProbeX)),
      Math.min(100, Math.max(0, nextProbeY)),
    ];
  }

  function handlePointerDown(event: ThreeEvent<PointerEvent>) {
    event.stopPropagation();
    setDragging(true);
    updateFromPoint(event);
  }

  function handlePointerMove(event: ThreeEvent<PointerEvent>) {
    if (!dragging) {
      return;
    }
    updateFromPoint(event);
  }

  function handlePointerUp(event: ThreeEvent<PointerEvent>) {
    event.stopPropagation();
    setDragging(false);
  }

  return (
    <mesh
      position={[0, 0.55, 1.15]}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
    >
      <planeGeometry args={[4.4, 2.6]} />
      <meshBasicMaterial transparent opacity={0} />
    </mesh>
  );
}

function BeamModel({
  focalDepth,
  intensity,
  probeX,
  probeY,
}: Pick<ViewportSceneProps, "focalDepth" | "intensity" | "probeX" | "probeY">) {
  const beamLength = Math.max(1.2, Math.min(3.4, focalDepth / 24));
  const beamRadius = Math.max(0.08, Math.min(0.24, intensity * 0.16));
  const x = ((probeX - 50) / 50) * 1.1;
  const y = ((50 - probeY) / 50) * 0.95 + 0.55;

  return (
    <mesh position={[x, y, 0.25]} rotation={[1.15, 0, 0]} receiveShadow>
      <cylinderGeometry args={[beamRadius, 0.03, beamLength, 24, 1, true]} />
      <meshStandardMaterial
        color="#d6714f"
        emissive="#b65937"
        emissiveIntensity={0.55}
        transparent
        opacity={0.28}
        side={2}
      />
    </mesh>
  );
}

export function ViewportScene(props: ViewportSceneProps) {
  const [model, setModel] = useState<AnatomyModel>(fallbackAnatomyModel);
  const [headEntryCount, setHeadEntryCount] = useState<number | null>(null);

  useEffect(() => {
    let active = true;

    async function loadModel() {
      try {
        const [modelResponse, metadataResponse, phantomResponse, tissueResponse] =
          await Promise.all([
          fetch("/anatomy/xcat-proxy.model.json"),
          fetch("/anatomy/bodyparts3d-head-metadata.json"),
          fetch("/anatomy/phantom.manifest.json"),
          fetch("/anatomy/tissue-properties.json"),
          ]);

        if (!active) {
          return;
        }

        if (modelResponse.ok) {
          const nextModel = (await modelResponse.json()) as AnatomyModel;
          setModel(nextModel);
        }

        const metadata = metadataResponse.ok
          ? ((await metadataResponse.json()) as {
              entryCount: number;
              entries: AnatomyModel["bodyParts3dHeadEntries"];
            })
          : null;
        const phantomManifest = phantomResponse.ok
          ? ((await phantomResponse.json()) as AnatomyModel["phantomManifest"])
          : null;
        const tissueProperties = tissueResponse.ok
          ? ((await tissueResponse.json()) as AnatomyModel["tissueProperties"])
          : null;

        setHeadEntryCount(metadata?.entryCount ?? null);
        setModel((currentModel) => ({
          ...currentModel,
          bodyParts3dHeadEntries: metadata?.entries ?? [],
          phantomManifest: phantomManifest ?? undefined,
          tissueProperties: tissueProperties ?? undefined,
        }));
      } catch {
        if (active) {
          setModel(fallbackAnatomyModel);
        }
      }
    }

    void loadModel();

    return () => {
      active = false;
    };
  }, []);

  const modelMetadata = useMemo(
    () => ({
      source: model.source,
      layerCount: model.layers.length,
    }),
    [model],
  );

  return (
    <div className="scene-shell">
      <Canvas camera={{ position: [0, 1.4, 4.6], fov: 38 }} shadows>
        <color attach="background" args={["#efe6d9"]} />
        <fog attach="fog" args={["#efe6d9", 4.6, 8.5]} />
        <ambientLight intensity={1.2} />
        <directionalLight
          castShadow
          intensity={1.35}
          position={[4, 6, 5]}
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />
        <pointLight intensity={0.6} position={[-3, 2, 3]} color="#f6d8c6" />

        <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.9, 0]}>
          <circleGeometry args={[5, 64]} />
          <meshStandardMaterial color="#e1d4c4" />
        </mesh>

        <Suspense fallback={null}>
          <HeadModel model={model} />
        </Suspense>
        <ProbeModel {...props} />
        <BeamModel {...props} />
        <ProbeDragSurface
          onProbePoseChange={props.onProbePoseChange}
          probeRotation={props.probeRotation}
        />
        <OrbitControls enablePan={false} minDistance={3.4} maxDistance={7} />
      </Canvas>
      <div className="scene-badge">
        <strong>{model.name}</strong>
        <span>
          {modelMetadata.layerCount} layers from {modelMetadata.source}
        </span>
        {model.phantomManifest ? (
          <span>
            phantom {model.phantomManifest.id} / {model.phantomManifest.version}
          </span>
        ) : null}
        {model.tissueProperties ? (
          <span>{model.tissueProperties.tissues.length} tissue classes loaded</span>
        ) : null}
        {headEntryCount !== null ? (
          <span>{headEntryCount} head-related BodyParts3D entries indexed</span>
        ) : null}
      </div>
      <div className="scene-hint">Drag in the viewport to move the probe target.</div>
    </div>
  );
}

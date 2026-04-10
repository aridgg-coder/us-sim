"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas, ThreeEvent, useLoader } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Euler, Mesh, Quaternion, Vector3 } from "three";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";

import { AnatomyModel, fallbackAnatomyModel } from "../lib/anatomy";
import { computeProbePose } from "../lib/probePose";

type ViewportSceneProps = {
  probeX: number;
  probeY: number;
  probeRotation: number;
  focalDepth: number;
  intensity: number;
  onProbePoseChange: (pose: { x: number; y: number }) => void;
};

function HeadModel({ model }: { model: AnatomyModel }) {
  const hasOuterHeadMesh = (model.meshes ?? []).some(
    (mesh) => mesh.id === "synthetic-head-outer",
  );

  return (
    <group rotation={[0.2, -0.35, 0]}>
      {model.layers.map((layer) => {
        if (hasOuterHeadMesh && layer.id === "scalp") {
          return null;
        }

        return (
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
        );
      })}
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
  const pose = useMemo(
    () => computeProbePose(probeX, probeY, probeRotation),
    [probeRotation, probeX, probeY],
  );

  return (
    <group position={pose.probePosition} rotation={pose.probeRotation}>
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
}: Pick<ViewportSceneProps, "onProbePoseChange">) {
  const [dragging, setDragging] = useState(false);

  function updateFromPoint(event: ThreeEvent<PointerEvent>) {
    const nextX = Math.min(100, Math.max(0, ((event.point.x + 2.2) / 4.4) * 100));
    const nextY = Math.min(100, Math.max(0, 50 - ((event.point.y - 0.3) / 2.6) * 50));
    onProbePoseChange({
      x: Number(nextX.toFixed(1)),
      y: Number(nextY.toFixed(1)),
    });
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
  probeRotation,
}: Pick<ViewportSceneProps, "focalDepth" | "intensity" | "probeX" | "probeY" | "probeRotation">) {
  const beamLength = Math.max(1.2, Math.min(3.4, focalDepth / 24));
  const beamRadius = Math.max(0.08, Math.min(0.24, intensity * 0.16));
  const pose = useMemo(
    () => computeProbePose(probeX, probeY, probeRotation),
    [probeRotation, probeX, probeY],
  );
  const beamDirection = useMemo(
    () => pose.probeAxis.map((value) => -value) as [number, number, number],
    [pose.probeAxis],
  );
  const beamPosition = useMemo(
    () => [
      pose.contactPoint[0] + (beamDirection[0] * beamLength) / 2,
      pose.contactPoint[1] + (beamDirection[1] * beamLength) / 2,
      pose.contactPoint[2] + (beamDirection[2] * beamLength) / 2,
    ] as [number, number, number],
    [beamDirection, beamLength, pose.contactPoint],
  );
  const beamRotation = useMemo(() => {
    const quaternion = new Quaternion().setFromUnitVectors(
      new Vector3(0, 1, 0),
      new Vector3(...beamDirection).normalize(),
    );
    const euler = new Euler().setFromQuaternion(quaternion, "XYZ");
    return [euler.x, euler.y, euler.z] as [number, number, number];
  }, [beamDirection]);

  return (
    <mesh position={beamPosition} rotation={beamRotation} receiveShadow>
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
        <ProbeDragSurface onProbePoseChange={props.onProbePoseChange} />
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

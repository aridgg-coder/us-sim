"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

type SimulationResponse = {
  job_id: string;
  status: "queued" | "running" | "completed";
  simulation_engine: "baseline" | "tusx" | "babelbrain";
  engine_metadata: {
    engine: "baseline" | "tusx" | "babelbrain";
    adapter_version: string;
    run_directory: string;
    manifest_path: string;
    handoff_path: string;
    tusx_input_path: string;
    created_at_utc: string;
  };
  grayscale_image_url: string;
  anatomy_model_id: string;
  phantom_version: string;
  summary: {
    attenuation_estimate: number;
    focal_region_depth_mm: number;
    estimated_latency_ms: number;
    reflection_estimate: number;
  };
  path_segments: Array<{
    structure_id: string;
    tissue_id: string;
    length_mm: number;
    attenuation_contribution: number;
  }>;
  region_hits: Array<{
    structure_id: string;
    label: string;
    hit_strength: number;
  }>;
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const ViewportScene = dynamic(
  () =>
    import("./ViewportScene").then((module) => ({
      default: module.ViewportScene,
    })),
  {
    ssr: false,
    loading: () => <div className="scene-loading">Loading 3D viewport...</div>,
  },
);

export function SimulationWorkbench() {
  const [frequency, setFrequency] = useState("2.5");
  const [focalDepth, setFocalDepth] = useState("55");
  const [gain, setGain] = useState("18");
  const [intensity, setIntensity] = useState("0.7");
  const [contactAngle, setContactAngle] = useState("12");
  const [couplingQuality, setCouplingQuality] = useState("0.92");
  const [probeX, setProbeX] = useState("18");
  const [probeY, setProbeY] = useState("42");
  const [probeRotation, setProbeRotation] = useState("-23");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResponse | null>(null);

  function constrainProbePose(
    probeXValue: number,
    probeYValue: number,
    probeRotationValue: number,
  ): { x: number; y: number } {
    // Constrain to the visible outer scalp shell (fallback layer), not the inner sphere.
    const HEAD_LOCAL_CENTER: [number, number, number] = [0, -0.08, 0];
    const HEAD_GROUP_ROT_X = 0.2;
    const HEAD_GROUP_ROT_Y = -0.35;
    const HEAD_GROUP_ROT_Z = 0;
    const HEAD_RADIUS = 1.66;
    const PROBE_Z = 0.85;
    const PROBE_ROT_X = 0.55;
    const PROBE_ROT_Y = 0.1;
    const PROBE_ROT_Z = (probeRotationValue * Math.PI) / 180;

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

    let probeX3d = ((probeXValue - 50) / 50) * 1.3;
    let probeY3d = ((50 - probeYValue) / 50) * 1.1 + 1.25;

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

          if (safeXY <= 1e-6) {
            correctionX += penetrationXY;
            continue;
          }

          correctionX += nx * penetrationXY;
          correctionY += ny * penetrationXY;
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

    return {
      x: Math.min(100, Math.max(0, nextProbeX)),
      y: Math.min(100, Math.max(0, nextProbeY)),
    };
  }

  function handleProbePoseChange(nextPose: { x: number; y: number }) {
    const constrained = constrainProbePose(nextPose.x, nextPose.y, Number(probeRotation));
    setProbeX(constrained.x.toFixed(1));
    setProbeY(constrained.y.toFixed(1));
  }

  function handleProbeXChange(nextX: string) {
    const constrained = constrainProbePose(
      Number(nextX),
      Number(probeY),
      Number(probeRotation),
    );
    setProbeX(constrained.x.toFixed(1));
    setProbeY(constrained.y.toFixed(1));
  }

  function handleProbeYChange(nextY: string) {
    const constrained = constrainProbePose(
      Number(probeX),
      Number(nextY),
      Number(probeRotation),
    );
    setProbeX(constrained.x.toFixed(1));
    setProbeY(constrained.y.toFixed(1));
  }

  function handleProbeRotationChange(nextRotation: string) {
    const constrained = constrainProbePose(
      Number(probeX),
      Number(probeY),
      Number(nextRotation),
    );
    setProbeRotation(nextRotation);
    setProbeX(constrained.x.toFixed(1));
    setProbeY(constrained.y.toFixed(1));
  }

  async function runSimulation() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/simulations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          anatomy_model_id: "baseline-head-phantom-v1",
          phantom_version: "baseline-v1",
          probe_pose: {
            position_mm: {
              x: Number(probeX),
              y: Number(probeY),
              z: 0,
            },
            rotation_deg: {
              x: 0,
              y: 0,
              z: Number(probeRotation),
            },
          },
          ultrasound_parameters: {
            frequency_mhz: Number(frequency),
            focal_depth_mm: Number(focalDepth),
            gain_db: Number(gain),
            intensity: Number(intensity),
            contact_angle_deg: Number(contactAngle),
            coupling_quality: Number(couplingQuality),
          },
          output_mode: "baseline",
        }),
      });

      if (!response.ok) {
        throw new Error(`Simulation request failed with ${response.status}`);
      }

      const payload: SimulationResponse = await response.json();
      setResult(payload);
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Unknown simulation error";
      setError(message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const outputRows = result
    ? [
        { label: "Job status", value: result.status },
        {
          label: "Attenuation",
          value: result.summary.attenuation_estimate.toFixed(3),
        },
        {
          label: "Focal depth",
          value: `${result.summary.focal_region_depth_mm} mm`,
        },
        {
          label: "Latency",
          value: `${result.summary.estimated_latency_ms} ms`,
        },
        {
          label: "Phantom",
          value: result.phantom_version,
        },
        {
          label: "Anatomy",
          value: result.anatomy_model_id,
        },
        {
          label: "Engine",
          value: result.simulation_engine,
        },
        {
          label: "Adapter",
          value: result.engine_metadata.adapter_version,
        },
        {
          label: "Reflection",
          value: result.summary.reflection_estimate.toFixed(3),
        },
      ]
    : [
        { label: "Primary image", value: "Grayscale B-mode preview" },
        { label: "Beam path", value: "Visible in 3D scene" },
        { label: "Attenuation", value: "Semi-quantitative estimate" },
        { label: "Job latency", value: "Short async compute allowed" },
      ];

  const probeStyle = {
    left: `${probeX}%`,
    top: `${probeY}%`,
  };

  return (
    <main className="workspace">
      <section className="hero">
        <p className="eyebrow">Research Workspace</p>
        <h1>US Probe / Head Simulation</h1>
        <p className="lede">
          Starter shell for a 3D research tool with manipulable probe placement,
          grayscale image output, and semi-quantitative simulation results.
        </p>
      </section>

      <section className="grid">
        <article className="panel viewport">
          <div className="panel-header">
            <h2>3D Viewport</h2>
            <span>Head model + probe pose</span>
          </div>
          <div className="viewport-stage">
            <ViewportScene
              probeX={Number(probeX)}
              probeY={Number(probeY)}
              probeRotation={Number(probeRotation)}
              focalDepth={Number(focalDepth)}
              intensity={Number(intensity)}
              onProbePoseChange={handleProbePoseChange}
            />
            <div className="probe-projection" style={probeStyle} />
          </div>
          <p className="panel-note">
            The viewport now uses anatomy data definitions and supports direct
            in-scene probe dragging. Next step: swap the proxy anatomy adapter
            for imported XCAT and public-source volumes.
          </p>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Probe Parameters</h2>
            <span>Interactive controls</span>
          </div>
          <div className="control-list">
            <label>
              <span>Frequency (MHz)</span>
              <input
                type="number"
                step="0.1"
                value={frequency}
                onChange={(event) => setFrequency(event.target.value)}
              />
            </label>
            <label>
              <span>Focal depth (mm)</span>
              <input
                type="number"
                step="1"
                value={focalDepth}
                onChange={(event) => setFocalDepth(event.target.value)}
              />
            </label>
            <label>
              <span>Gain (dB)</span>
              <input
                type="number"
                step="1"
                value={gain}
                onChange={(event) => setGain(event.target.value)}
              />
            </label>
            <label>
              <span>Intensity</span>
              <input
                type="number"
                step="0.05"
                value={intensity}
                onChange={(event) => setIntensity(event.target.value)}
              />
            </label>
            <label>
              <span>Contact angle (deg)</span>
              <input
                type="number"
                step="1"
                value={contactAngle}
                onChange={(event) => setContactAngle(event.target.value)}
              />
            </label>
            <label>
              <span>Coupling quality</span>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={couplingQuality}
                onChange={(event) => setCouplingQuality(event.target.value)}
              />
            </label>
            <label>
              <span>Probe X (%)</span>
              <input
                type="range"
                min="0"
                max="100"
                value={probeX}
                onChange={(event) => handleProbeXChange(event.target.value)}
              />
              <output>{probeX}%</output>
            </label>
            <label>
              <span>Probe Y (%)</span>
              <input
                type="range"
                min="0"
                max="100"
                value={probeY}
                onChange={(event) => handleProbeYChange(event.target.value)}
              />
              <output>{probeY}%</output>
            </label>
            <label>
              <span>Probe rotation (deg)</span>
              <input
                type="range"
                min="-90"
                max="90"
                value={probeRotation}
                onChange={(event) => handleProbeRotationChange(event.target.value)}
              />
              <output>{probeRotation} deg</output>
            </label>
          </div>
          <button className="run-button" onClick={runSimulation} disabled={loading}>
            {loading ? "Running simulation..." : "Run simulation"}
          </button>
          {error ? <p className="error-text">{error}</p> : null}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Simulation Outputs</h2>
            <span>Baseline targets</span>
          </div>
          <ul className="metric-list">
            {outputRows.map((output) => (
              <li key={output.label}>
                <span>{output.label}</span>
                <strong>{output.value}</strong>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Path Segments</h2>
            <span>Tissue traversal</span>
          </div>
          <ul className="metric-list">
            {(result?.path_segments ?? []).map((segment) => (
              <li key={segment.structure_id}>
                <span>
                  {segment.structure_id} / {segment.tissue_id}
                </span>
                <strong>
                  {segment.length_mm} mm, attn {segment.attenuation_contribution}
                </strong>
              </li>
            ))}
            {!result ? (
              <li>
                <span>Pending</span>
                <strong>Run a simulation to inspect tissue traversal</strong>
              </li>
            ) : null}
          </ul>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Region Hits</h2>
            <span>Relative beam interaction</span>
          </div>
          <ul className="metric-list">
            {(result?.region_hits ?? []).map((region) => (
              <li key={region.structure_id}>
                <span>{region.label}</span>
                <strong>{region.hit_strength.toFixed(3)}</strong>
              </li>
            ))}
            {!result ? (
              <li>
                <span>Pending</span>
                <strong>Run a simulation to inspect region hit strength</strong>
              </li>
            ) : null}
          </ul>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Engine Metadata</h2>
            <span>Adapter provenance</span>
          </div>
          <ul className="metric-list">
            {result ? (
              <>
                <li>
                  <span>Run directory</span>
                  <strong>{result.engine_metadata.run_directory}</strong>
                </li>
                <li>
                  <span>Manifest</span>
                  <strong>{result.engine_metadata.manifest_path}</strong>
                </li>
                <li>
                  <span>Handoff</span>
                  <strong>{result.engine_metadata.handoff_path}</strong>
                </li>
                {result.engine_metadata.tusx_input_path ? (
                  <li>
                    <span>TUSX input</span>
                    <strong>{result.engine_metadata.tusx_input_path}</strong>
                  </li>
                ) : null}
                <li>
                  <span>Created</span>
                  <strong>{result.engine_metadata.created_at_utc}</strong>
                </li>
              </>
            ) : (
              <li>
                <span>Pending</span>
                <strong>Run a simulation to inspect engine provenance</strong>
              </li>
            )}
          </ul>
        </article>

        <article className="panel image-panel">
          <div className="panel-header">
            <h2>Grayscale Image</h2>
            <span>{result ? result.grayscale_image_url : "Placeholder render"}</span>
          </div>
          <div className="grayscale-preview" />
        </article>
      </section>
    </main>
  );
}

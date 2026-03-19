export type AnatomyLayer = {
  id: string;
  label: string;
  color: string;
  opacity: number;
  scale: [number, number, number];
  position: [number, number, number];
};

export type AnatomyLandmark = {
  id: string;
  label: string;
  position: [number, number, number];
};

export type AnatomyMesh = {
  id: string;
  label: string;
  url: string;
  color: string;
  opacity?: number;
  scale?: [number, number, number];
  position?: [number, number, number];
  rotationDeg?: [number, number, number];
};

export type ExternalAnatomyReference = {
  source: string;
  url: string;
  notes: string;
};

export type BodyParts3DEntry = {
  conceptId: string;
  representationId: string;
  label: string;
};

export type PhantomStructure = {
  id: string;
  label: string;
  tissueId: string;
  renderLayerId: string;
};

export type ProbeTarget = {
  id: string;
  label: string;
  landmarkId: string;
};

export type PhantomManifest = {
  id: string;
  version: string;
  name: string;
  description: string;
  coordinateSystem: {
    handedness: string;
    units: string;
    axes: {
      x: string;
      y: string;
      z: string;
    };
  };
  structures: PhantomStructure[];
  probeTargets: ProbeTarget[];
  sourcePolicy: {
    primary: string;
    secondary: string;
    fallback: string;
  };
  provenance: ExternalAnatomyReference[];
};

export type TissueProperty = {
  id: string;
  label: string;
  soundSpeed: number;
  density: number;
  attenuation: number;
  impedance: number;
};

export type TissuePropertyTable = {
  version: string;
  units: {
    soundSpeed: string;
    density: string;
    attenuation: string;
    impedance: string;
  };
  tissues: TissueProperty[];
  notes: string[];
};

export type AnatomyModel = {
  id: string;
  name: string;
  source: string;
  description: string;
  layers: AnatomyLayer[];
  landmarks: AnatomyLandmark[];
  meshes?: AnatomyMesh[];
  references?: ExternalAnatomyReference[];
  bodyParts3dHeadEntries?: BodyParts3DEntry[];
  phantomManifest?: PhantomManifest;
  tissueProperties?: TissuePropertyTable;
};

export const fallbackAnatomyModel: AnatomyModel = {
  id: "xcat-default",
  name: "XCAT-inspired Head Model",
  source: "Local fallback proxy",
  description:
    "Fallback layered anatomical proxy used when public manifest loading is unavailable.",
  layers: [
    {
      id: "scalp",
      label: "Scalp",
      color: "#d9d0c3",
      opacity: 0.92,
      scale: [1.48, 1.66, 1.44],
      position: [0, -0.08, 0],
    },
    {
      id: "skull",
      label: "Skull",
      color: "#f2ece4",
      opacity: 0.42,
      scale: [1.24, 1.42, 1.2],
      position: [0, -0.02, 0.05],
    },
    {
      id: "csf",
      label: "CSF",
      color: "#efe8dc",
      opacity: 0.16,
      scale: [1.13, 1.27, 1.06],
      position: [0.01, 0.02, 0.06],
    },
    {
      id: "brain",
      label: "Brain",
      color: "#b5a696",
      opacity: 0.64,
      scale: [1.08, 1.18, 1.01],
      position: [0.02, 0.02, 0.08],
    },
  ],
  landmarks: [
    {
      id: "frontal",
      label: "Frontal target",
      position: [0.18, 0.42, 0.3],
    },
    {
      id: "temporal",
      label: "Temporal window",
      position: [0.98, 0.28, 0.36],
    },
  ],
};

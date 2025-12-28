"""Curated v1 compliance/certification pathway mappings (FMVSS/UNECE focus)."""

from __future__ import annotations

V1_VERSION = "1.0"
V1_SCOPE = "EV conversion / modified vehicle compliance pathway (high-level mapping; not legal advice)."

STANDARDS = [
  {"id":"FMVSS_108","jur":"US","title":"Lamps, reflective devices, and associated equipment","scope":"lighting/visibility"},
  {"id":"FMVSS_105","jur":"US","title":"Hydraulic brake systems","scope":"braking"},
  {"id":"FMVSS_121","jur":"US","title":"Air brake systems","scope":"braking (if air)"},
  {"id":"FMVSS_135","jur":"US","title":"Light vehicle brake systems","scope":"braking (light vehicles)"},
  {"id":"FMVSS_111","jur":"US","title":"Rear visibility","scope":"camera/display (if modified)"},
  {"id":"FMVSS_114","jur":"US","title":"Theft protection","scope":"immobilizer/start control (if altered)"},
  {"id":"FMVSS_138","jur":"US","title":"Tire pressure monitoring systems","scope":"TPMS (if affected)"},
  {"id":"FMVSS_208","jur":"US","title":"Occupant crash protection","scope":"restraints/airbags (avoid impact)"},
  {"id":"FMVSS_209","jur":"US","title":"Seat belt assemblies","scope":"restraints (avoid impact)"},
  {"id":"FMVSS_210","jur":"US","title":"Seat belt assembly anchorages","scope":"restraints (avoid impact)"},
  {"id":"FMVSS_301","jur":"US","title":"Fuel system integrity","scope":"crash integrity (ICE); EV mods can implicate equivalent safety"},
  {"id":"UNECE_R10","jur":"UNECE","title":"Electromagnetic compatibility","scope":"EMC (vehicle & components)"},
  {"id":"UNECE_R13H","jur":"UNECE","title":"Braking of M1/N1 vehicles","scope":"braking"},
  {"id":"UNECE_R13","jur":"UNECE","title":"Braking of M2/M3/N2/N3 vehicles","scope":"braking"},
  {"id":"UNECE_R48","jur":"UNECE","title":"Installation of lighting and light-signalling devices","scope":"lighting installation"},
  {"id":"UNECE_R6","jur":"UNECE","title":"Direction indicators","scope":"lighting component"},
  {"id":"UNECE_R7","jur":"UNECE","title":"Position, stop and end-outline marker lamps","scope":"lighting component"},
  {"id":"UNECE_R23","jur":"UNECE","title":"Reversing lamps","scope":"lighting component"},
  {"id":"UNECE_R38","jur":"UNECE","title":"Rear fog lamps","scope":"lighting component"},
  {"id":"UNECE_R112","jur":"UNECE","title":"Headlamps for asymmetrical passing beam/driving beam","scope":"lighting component"},
  {"id":"UNECE_R100","jur":"UNECE","title":"Electric power train safety","scope":"HV electrical safety / RESS"},
  {"id":"UNECE_R79","jur":"UNECE","title":"Steering equipment","scope":"steering (if changed)"},
  {"id":"UNECE_R34","jur":"UNECE","title":"Fire risks","scope":"fire / fuel / electric safety"},
]

TESTS = [
  {"id":"EMC_VEHICLE","name":"Vehicle EMC (radiated/conducted emissions & immunity)","refs":["UNECE_R10"],"tags":["EMC"]},
  {"id":"HV_ELECTRICAL_SAFETY","name":"HV electrical safety: isolation resistance, protection against electric shock, IP, discharge times","refs":["UNECE_R100"],"tags":["HV","safety"]},
  {"id":"RESS_ABUSE","name":"RESS safety: overcharge/overdischarge, external short, thermal propagation evidence, venting, containment","refs":["UNECE_R100"],"tags":["battery","safety"]},
  {"id":"BRAKE_PERFORMANCE","name":"Brake performance (service/secondary/parking; fade, recovery; regen coordination if applicable)","refs":["FMVSS_105","FMVSS_135","UNECE_R13H"],"tags":["braking"]},
  {"id":"LIGHTING_AIM_OUTPUT","name":"Lighting photometry/aim/installation verification","refs":["FMVSS_108","UNECE_R48","UNECE_R112"],"tags":["lighting"]},
  {"id":"LABELING_WARNINGS","name":"Labeling/marking: HV warnings, component labels, service disconnect marking, VIN/altered vehicle disclosures","refs":["UNECE_R100","FMVSS_108"],"tags":["labeling","documentation"]},
  {"id":"OBD_DIAGNOSTICS_CHECK","name":"Diagnostic & telltale sanity checks (ABS/ESC/TPMS/charge status as applicable)","refs":["FMVSS_138","FMVSS_105","FMVSS_135"],"tags":["diagnostics"]},
]

DOC_CHECKLIST = [
  {"id":"DOC_BUILD_RECORD","name":"Conversion build record (as-built BOM, torque logs, photos, serials, calibration versions)","category":"build"},
  {"id":"DOC_HV_SCHEMATIC","name":"HV electrical schematic & harness routing, fusing, contactors, interlocks, service disconnect","category":"engineering"},
  {"id":"DOC_SW_SAFETY","name":"Software/controls summary: torque/regen strategy, derates, interlocks, fault handling, cybersecurity basics","category":"engineering"},
  {"id":"DOC_RISK_ASSESS","name":"Hazard analysis (HV shock, thermal, fire, runaway; mitigations & verification evidence)","category":"safety"},
  {"id":"DOC_TEST_PLAN_REPORTS","name":"Test plan + reports (EMC, HV safety, braking, lighting checks, labeling verification)","category":"verification"},
  {"id":"DOC_USER_MANUAL","name":"Owner/operator info: charging, limitations, warnings, emergency response notes","category":"customer"},
  {"id":"DOC_SERVICE_MANUAL","name":"Service procedures: de-energization, PPE, isolation test, crash recovery, towing/jacking","category":"service"},
  {"id":"DOC_LABEL_SET","name":"Label/placard set: HV warning, disconnect location, battery chemistry, fuse ratings, emergency cut loop (if used)","category":"labeling"},
  {"id":"DOC_TRACEABILITY","name":"Component compliance evidence: supplier CoCs, UN38.3 (if shipping), E-marks where relevant","category":"supply"},
]

COMPONENTS = [
  {"id":"BATTERY_PACK","name":"Battery pack (RESS)","group":"powertrain"},
  {"id":"BMS","name":"Battery management system","group":"controls"},
  {"id":"INVERTER","name":"Inverter / motor controller","group":"powertrain"},
  {"id":"MOTOR","name":"Traction motor","group":"powertrain"},
  {"id":"DC_DC","name":"DC-DC converter","group":"powertrain"},
  {"id":"OBC","name":"On-board charger / charge inlet","group":"charging"},
  {"id":"HV_HARNESS","name":"HV cables, connectors, service disconnect, HVIL","group":"electrical"},
  {"id":"CONTACTORS_FUSING","name":"Contactors, precharge, fusing","group":"electrical"},
  {"id":"REGEN_BRAKING","name":"Regenerative braking integration","group":"braking"},
  {"id":"FRICTION_BRAKES","name":"Friction brake system (hydraulic/air)","group":"braking"},
  {"id":"LIGHTING","name":"Exterior lighting (if altered)","group":"body"},
  {"id":"LABELING","name":"Labels/markings/warnings","group":"documentation"},
]

CROSSWALK = [
  {"component":"BATTERY_PACK","standards":["UNECE_R100","UNECE_R34"],"tests":["HV_ELECTRICAL_SAFETY","RESS_ABUSE","LABELING_WARNINGS"],"docs":["DOC_HV_SCHEMATIC","DOC_RISK_ASSESS","DOC_TEST_PLAN_REPORTS","DOC_LABEL_SET","DOC_TRACEABILITY"]},
  {"component":"BMS","standards":["UNECE_R100","UNECE_R10"],"tests":["EMC_VEHICLE","HV_ELECTRICAL_SAFETY"],"docs":["DOC_SW_SAFETY","DOC_TEST_PLAN_REPORTS","DOC_TRACEABILITY"]},
  {"component":"INVERTER","standards":["UNECE_R10","UNECE_R100"],"tests":["EMC_VEHICLE","HV_ELECTRICAL_SAFETY"],"docs":["DOC_HV_SCHEMATIC","DOC_TEST_PLAN_REPORTS","DOC_TRACEABILITY"]},
  {"component":"MOTOR","standards":["UNECE_R10"],"tests":["EMC_VEHICLE"],"docs":["DOC_BUILD_RECORD","DOC_TRACEABILITY"]},
  {"component":"DC_DC","standards":["UNECE_R10","UNECE_R100"],"tests":["EMC_VEHICLE","HV_ELECTRICAL_SAFETY"],"docs":["DOC_HV_SCHEMATIC","DOC_TRACEABILITY"]},
  {"component":"OBC","standards":["UNECE_R10","UNECE_R100"],"tests":["EMC_VEHICLE","HV_ELECTRICAL_SAFETY","LABELING_WARNINGS"],"docs":["DOC_USER_MANUAL","DOC_SERVICE_MANUAL","DOC_LABEL_SET","DOC_TRACEABILITY"]},
  {"component":"HV_HARNESS","standards":["UNECE_R100"],"tests":["HV_ELECTRICAL_SAFETY","LABELING_WARNINGS"],"docs":["DOC_HV_SCHEMATIC","DOC_SERVICE_MANUAL","DOC_LABEL_SET"]},
  {"component":"CONTACTORS_FUSING","standards":["UNECE_R100"],"tests":["HV_ELECTRICAL_SAFETY"],"docs":["DOC_HV_SCHEMATIC","DOC_BUILD_RECORD"]},
  {"component":"REGEN_BRAKING","standards":["FMVSS_105","FMVSS_135","UNECE_R13H"],"tests":["BRAKE_PERFORMANCE","OBD_DIAGNOSTICS_CHECK"],"docs":["DOC_SW_SAFETY","DOC_TEST_PLAN_REPORTS"]},
  {"component":"FRICTION_BRAKES","standards":["FMVSS_105","FMVSS_135","FMVSS_121","UNECE_R13H","UNECE_R13"],"tests":["BRAKE_PERFORMANCE"],"docs":["DOC_BUILD_RECORD","DOC_TEST_PLAN_REPORTS"]},
  {"component":"LIGHTING","standards":["FMVSS_108","UNECE_R48","UNECE_R6","UNECE_R7","UNECE_R23","UNECE_R38","UNECE_R112"],"tests":["LIGHTING_AIM_OUTPUT"],"docs":["DOC_BUILD_RECORD","DOC_TEST_PLAN_REPORTS"]},
  {"component":"LABELING","standards":["UNECE_R100","FMVSS_108"],"tests":["LABELING_WARNINGS"],"docs":["DOC_LABEL_SET","DOC_USER_MANUAL","DOC_SERVICE_MANUAL"]},
]

DECISION_TREE = {
  "id":"CERT_PATH_V1",
  "title":"Initial certification strategy decision tree (v1)",
  "nodes":[
    {"id":"START","q":"Where will the converted vehicle be registered/placed on market?","type":"choice",
     "choices":[
       {"a":"US (FMVSS self-certification)","next":"US_PATH"},
       {"a":"UNECE / EU-UK aligned type approval","next":"UNECE_PATH"},
       {"a":"Mixed/uncertain","next":"DUAL_PATH"},
     ]},
    {"id":"US_PATH","q":"Are you a manufacturer of record for sale, or modifying a customer-owned vehicle?","type":"choice",
     "choices":[
       {"a":"Sale / manufacturer of record","next":"US_MFR"},
       {"a":"Owner modification / upfitter","next":"US_UPFITTER"},
     ]},
    {"id":"US_MFR","q":"Did the conversion affect systems covered by key FMVSS (108 lighting, braking 105/135/121, restraints 208/209/210, rear visibility 111, TPMS 138)?","type":"choice",
     "choices":[
       {"a":"Yes/likely","next":"US_TEST_EVIDENCE"},
       {"a":"No/minimal","next":"US_DOC_ONLY"},
     ]},
    {"id":"US_TEST_EVIDENCE","q":"Can you generate objective evidence (test reports) for affected areas?","type":"choice",
     "choices":[
       {"a":"Yes","next":"OUTPUT_STRATEGY_US_FULL"},
       {"a":"Not yet","next":"OUTPUT_STRATEGY_US_GAP"},
     ]},
    {"id":"US_DOC_ONLY","q":"Proceed with build record + limited verification (lighting/braking sanity checks, HV safety, labeling).","type":"result",
     "result":"OUTPUT_STRATEGY_US_LIMITED"},
    {"id":"US_UPFITTER","q":"Ensure modifications do not render inoperative any FMVSS-required equipment; document deltas and checks.","type":"result",
     "result":"OUTPUT_STRATEGY_US_RENDER_INOP"},
    {"id":"UNECE_PATH","q":"Is type approval required (series production / market placement) or IVA-like individual approval?","type":"choice",
     "choices":[
       {"a":"Type approval","next":"UNECE_TA"},
       {"a":"Individual approval","next":"UNECE_IVA"},
     ]},
    {"id":"UNECE_TA","q":"Target core regs: R100 (HV safety/RESS), R10 (EMC), braking (R13H/R13), lighting install (R48). Engage technical service early.","type":"result",
     "result":"OUTPUT_STRATEGY_UNECE_TA"},
    {"id":"UNECE_IVA","q":"Use R100/R10/braking/lighting evidence; tailor to authority checklist; keep traceable build dossier.","type":"result",
     "result":"OUTPUT_STRATEGY_UNECE_IVA"},
    {"id":"DUAL_PATH","q":"Default to the strict union of evidence: R100+R10 + braking + lighting + labeling + robust documentation.","type":"result",
     "result":"OUTPUT_STRATEGY_DUAL"},
  ],
}

def get_v1_data() -> dict:
  """Return immutable-friendly v1 dataset payload."""
  return {
    "version": V1_VERSION,
    "scope": V1_SCOPE,
    "standards": list(STANDARDS),
    "tests": list(TESTS),
    "documentation_checklist": list(DOC_CHECKLIST),
    "components": list(COMPONENTS),
    "crosswalk": list(CROSSWALK),
    "decision_tree": dict(DECISION_TREE),
  }

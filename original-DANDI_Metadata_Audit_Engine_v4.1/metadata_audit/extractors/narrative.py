from __future__ import annotations

import re

from ..models import Evidence

# Narrative extraction is deliberately conservative. These are candidate values,
# not final answers. Every narrative hit keeps its supporting sentence and must be
# reviewed before it is treated as confirmed metadata.
PATTERNS: dict[str, list[tuple[str, str]]] = {
    "anaesthetic_type": [
        ("anaesthetic", r"\b(isoflurane|ketamine(?:[- ]xylazine)?|xylazine|urethane|sevoflurane|pentobarbital)\b"),
    ],
    "acquisition_equipment": [
        ("Blackrock recording system", r"\bBlackrock(?: Microsystems)?(?:[^.;]{0,50}?(?:recording|acquisition|Cerebus|CerePlex)[^.;]*)?\b"),
        ("MultiClamp", r"\bMultiClamp\s*700[AB]?\b"),
        ("Axopatch", r"\bAxopatch\s*\d+[A-Za-z]*\b"),
        ("Axoclamp", r"\bAxoclamp\s*\d+[A-Za-z]*\b"),
        ("Intan", r"\bIntan(?: Technologies)?(?:[^.;]{0,40}?(?:amplifier|headstage|recording system))?\b"),
        ("Open Ephys", r"\bOpen\s+Ephys(?:[^.;]{0,40}?acquisition system)?\b"),
        ("Plexon acquisition system", r"\bPlexon(?:[^.;]{0,60}?(?:acquisition system|MAP system|OmniPlex))\b"),
        ("amplifier", r"\b(?:patch[- ]clamp\s+)?amplifier\s+(?:was\s+)?(?:an\s+)?([A-Za-z0-9+_.\- ]{2,45})"),
    ],
    "equipment_manufacturer": [
        ("manufacturer", r"\b(Blackrock Microsystems|Molecular Devices|Axon Instruments|Plexon|Intan Technologies|Open Ephys|Scientifica|Sutter Instrument|HEKA|NPI Electronic)\b"),
    ],
    "acquisition_software": [
        ("Clampex", r"\bClampex\s*(?:version\s*)?[0-9.]*\b"),
        ("pCLAMP", r"\bpCLAMP\s*(?:version\s*)?[0-9.]*\b"),
        ("Open Ephys GUI", r"\bOpen\s+Ephys\s+GUI\b"),
        ("Spike2", r"\bSpike2\s*(?:version\s*)?[0-9.]*\b"),
        ("Cerebus", r"\bCerebus\b"),
        ("Central", r"\bBlackrock\s+Central\b"),
        ("LabVIEW", r"\bLabVIEW\b"),
        ("PatchMaster", r"\bPatchMaster\b"),
        ("WinWCP", r"\bWinWCP\b"),
    ],
    "analysis_software": [
        ("Plexon Offline Sorter", r"\bPlexon\s+Offline\s+Sorter\b"),
        ("Offline Sorter", r"\bOffline\s+Sorter\b"),
        ("Kilosort", r"\bKilosort(?:\s*[0-9.]+)?\b"),
        ("Clampfit", r"\bClampfit\s*(?:version\s*)?[0-9.]*\b"),
        ("Igor Pro", r"\bIgor\s+Pro\s*(?:version\s*)?[0-9.]*\b"),
        ("MATLAB", r"\bMATLAB\s*(?:R\d{4}[ab])?\b"),
        ("Python", r"\bPython\s*(?:version\s*)?[0-9.]*\b"),
    ],
    "electrode_or_probe": [
        ("Neuropixels", r"\bNeuropixels(?:\s*[12](?:\.0)?)?\b"),
        ("Utah array", r"\bUtah\s+array\b"),
        ("silicon probe", r"\b(?:silicon|multisite)\s+(?:electrode\s+)?probe\b"),
        ("tetrode", r"\b(?:tetrode|tetrodes)\b"),
        ("glass patch pipette", r"\b(?:borosilicate\s+)?glass\s+(?:patch\s+)?pipette(?:s)?\b"),
        ("patch pipette", r"\bpatch\s+pipette(?:s)?\b"),
        ("microelectrode array", r"\b(?:microelectrode|multielectrode)\s+array\b"),
    ],
    "probe_model": [
        ("probe model", r"\b(Neuropixels(?:\s*[12](?:\.0)?)?|Utah array|CerePlex\s*[A-Za-z0-9_.\-]+)\b"),
    ],
    "stimulation_equipment": [
        ("laser", r"\b(\d{3,4}(?:\.\d+)?\s*nm\s+(?:diode\s+)?laser)\b"),
        ("LED", r"\b(\d{3,4}(?:\.\d+)?\s*nm\s+LED)\b"),
    ],
    "injection_materials": [
        ("viral material", r"\b((?:r?AAV|CAV|HSV|lentivirus)[A-Za-z0-9_./+\-:]*)\b"),
    ],
    "titer": [
        ("titer", r"(\d+(?:\.\d+)?\s*[×x]\s*10\^?\d+\s*(?:GC|vg|TU)?\s*/\s*mL)"),
    ],
    "volume": [
        ("injection volume", r"(?:inject(?:ed|ion)?|infus(?:ed|ion)?)[^.;]{0,100}?(\d+(?:\.\d+)?)\s*(nL|µL|uL)"),
    ],
    "coordinates": [
        ("stereotaxic coordinates", r"(?:AP|anteroposterior)[^.;]{0,60}?(-?\d+(?:\.\d+)?)\s*mm[^.;]{0,80}?(?:ML|mediolateral)[^.;]{0,60}?(-?\d+(?:\.\d+)?)\s*mm[^.;]{0,80}?(?:DV|dorsoventral)[^.;]{0,60}?(-?\d+(?:\.\d+)?)\s*mm"),
    ],
    "laser_wavelength": [
        ("laser wavelength", r"(?:laser|optogenetic stimulation|light pulses?)[^.;]{0,100}?(\d{3,4}(?:\.\d+)?)\s*nm"),
    ],
    "excitation_wavelength": [
        ("excitation wavelength", r"(?:excitation|excited at|excited with)[^.;]{0,100}?(\d{3,4}(?:\.\d+)?)\s*nm"),
    ],
    "emission_wavelength": [
        ("emission wavelength", r"(?:emission(?:\s+filter|\s+wavelength)?|emitted|collected through|bandpass)[^.;]{0,100}?(\d{3,4}(?:\.\d+)?)\s*nm"),
    ],
    "experimental_model": [
        ("6-OHDA", r"\b6[- ]OHDA\b"),
        ("alpha-synuclein PFF", r"\b(?:α|alpha)[- ]synuclein[^.;]{0,50}?PFF\b"),
        ("LPS", r"\bLPS\b"),
    ],
}

TERMINAL_CONTEXT = re.compile(
    r"\b(perfus(?:e|ed|ion)|transcardial|euthani[sz]|sacrific(?:e|ed)|terminal(?:ly)?|fixation|fixed)\b",
    flags=re.IGNORECASE,
)
SURGERY_CONTEXT = re.compile(
    r"\b(surger|stereotax|implant|craniotom|inject|infus|drill|head[- ]?fix|anestheti[sz]ed for)\b",
    flags=re.IGNORECASE,
)


def _sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]


def _candidate_from_match(field: str, match: re.Match[str]) -> str:
    groups = [g.strip() for g in match.groups() if g is not None and str(g).strip()]
    candidate = " ".join(groups) if groups else match.group(0).strip()
    if field.endswith("wavelength") and re.fullmatch(r"\d+(?:\.\d+)?", candidate):
        candidate += " nm"
    return candidate


def _context_adjustment(field: str, sentence: str, source_location: str) -> tuple[str, str, str] | None:
    """Return (field, confidence, notes) or None when the hit should be ignored."""
    location_text = source_location.lower()

    if field == "anaesthetic_type":
        if TERMINAL_CONTEXT.search(sentence) or any(term in location_text for term in ("histology", "perfusion", "tissue processing")):
            return (
                "terminal_anaesthesia",
                "Medium",
                "Anaesthetic appears in terminal/perfusion context; do not use as surgical or acquisition anaesthesia.",
            )
        if SURGERY_CONTEXT.search(sentence) or any(term in location_text for term in ("surgery", "surgical", "stereotax")):
            return (
                "anaesthetic_type",
                "Medium",
                "Anaesthetic appears in a surgery-related context; confirm exact procedure before accepting.",
            )
        return (
            "anaesthetic_type",
            "Low",
            "Anaesthetic context is ambiguous; confirm whether it applies to surgery, acquisition, or another procedure.",
        )

    if field == "equipment_manufacturer" and re.search(r"offline sorter|software|analysis", sentence, re.IGNORECASE):
        return None

    return (field, "Medium", "Narrative candidate; confirm experimental context before accepting.")


def extract_narrative_evidence(
    text: str,
    source_type: str,
    source_location: str,
    doi: str = "",
    pmid: str = "",
    pmcid: str = "",
) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen: set[tuple[str, str, str]] = set()

    for sentence in _sentences(text):
        for field, patterns in PATTERNS.items():
            for label, pattern in patterns:
                match = re.search(pattern, sentence, flags=re.IGNORECASE)
                if not match:
                    continue

                adjusted = _context_adjustment(field, sentence, source_location)
                if adjusted is None:
                    continue
                output_field, confidence, context_note = adjusted
                candidate = _candidate_from_match(field, match)
                key = (output_field, candidate.casefold(), sentence.casefold())
                if key in seen:
                    continue
                seen.add(key)

                evidence.append(Evidence(
                    audit_field=output_field,
                    value=candidate,
                    source_type=source_type,
                    source_location=source_location,
                    confidence=confidence,
                    supporting_text=sentence,
                    review_status="Needs Manual Review",
                    notes=f"Narrative candidate ({label}). {context_note}",
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmcid,
                ))

    return evidence

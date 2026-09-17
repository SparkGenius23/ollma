"""Offline regression checks for the MaaS model-prompt contracts.

These tests intentionally read source files rather than importing the FastAPI
application.  They can therefore run in CI before Ollama, database drivers, or
deployment-only environment variables are available.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"
MAIN_PY = PROJECT_ROOT / "main.py"

EXPECTED_MODEL_FILES = {
    "Modelfile.chat",
    "Modelfile.recovery",
    "Modelfile.readiness",
    "Modelfile.risk",
    "Modelfile.overall",
}
SPECIALIST_FILES = EXPECTED_MODEL_FILES - {"Modelfile.chat"}
BASE_MODEL = "gpt-oss:20b"
JSON_ONLY_CONTRACT = "Return ONLY this JSON. No preamble, no markdown fences."
NO_RAW_DATA_ANALYSIS_CONTRACT = "You do NOT compute scores, identify drivers, or analyze raw data."
ECG_PROHIBITION = "Absolutely DO NOT offer medical advice, diagnosis, or interpret clinical waveforms (ECG/PPG)."


def model_mapping_from_source() -> dict[str, str]:
    """Read MODEL_MAPPING without importing optional production dependencies."""
    module = ast.parse(MAIN_PY.read_text(encoding="utf-8"), filename=str(MAIN_PY))
    for statement in module.body:
        if not isinstance(statement, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "MODEL_MAPPING" for target in statement.targets):
            mapping = ast.literal_eval(statement.value)
            if isinstance(mapping, dict) and all(isinstance(key, str) and isinstance(value, str) for key, value in mapping.items()):
                return mapping
            raise AssertionError("MODEL_MAPPING must be a literal string-to-string dictionary")
    raise AssertionError("main.py must define MODEL_MAPPING")


class ModelPromptContractTests(unittest.TestCase):
    def _content(self, filename: str) -> str:
        return (MODELS_DIR / filename).read_text(encoding="utf-8")

    def test_exactly_the_five_required_modelfiles_exist(self) -> None:
        self.assertTrue(MODELS_DIR.is_dir(), "models directory is required")
        self.assertEqual({path.name for path in MODELS_DIR.glob("Modelfile.*")}, EXPECTED_MODEL_FILES)

    def test_all_model_files_use_the_approved_base_model(self) -> None:
        for filename in sorted(EXPECTED_MODEL_FILES):
            with self.subTest(filename=filename):
                self.assertRegex(self._content(filename), rf"(?m)^FROM {re.escape(BASE_MODEL)}$")

    def test_runtime_mapping_matches_each_model_file_and_tag(self) -> None:
        mapping = model_mapping_from_source()
        model_names = {filename.removeprefix("Modelfile.") for filename in EXPECTED_MODEL_FILES}

        self.assertEqual(set(mapping), model_names)
        for model_name in sorted(model_names):
            with self.subTest(model_name=model_name):
                self.assertEqual(mapping[model_name], f"rhythmx-{model_name}:latest")

    def test_chat_model_retains_non_medical_and_symptom_safety_guards(self) -> None:
        content = self._content("Modelfile.chat")

        for required_phrase in (
            "non-medical, data-driven",
            ECG_PROHIBITION,
            "Base analysis STRICTLY on user-provided data",
            "If symptoms persist or worsen, please consult a medical professional.",
        ):
            with self.subTest(required_phrase=required_phrase):
                self.assertIn(required_phrase, content)

    def test_specialist_models_retain_data_boundary_and_json_only_contracts(self) -> None:
        for filename in sorted(SPECIALIST_FILES):
            with self.subTest(filename=filename):
                content = self._content(filename)
                self.assertIn(NO_RAW_DATA_ANALYSIS_CONTRACT, content)
                self.assertIn(JSON_ONLY_CONTRACT, content)

        risk_content = self._content("Modelfile.risk")
        self.assertIn("NEVER expose probability numbers or risk scores to the athlete", risk_content)

    def test_no_model_allows_raw_ecg_or_ppg_interpretation(self) -> None:
        # The chat prompt may mention ECG/PPG only in its explicit prohibition.
        # Every other occurrence would make the safety boundary ambiguous.
        for filename in sorted(EXPECTED_MODEL_FILES):
            with self.subTest(filename=filename):
                content = self._content(filename)
                if filename == "Modelfile.chat":
                    self.assertEqual(content.count(ECG_PROHIBITION), 1)
                    content = content.replace(ECG_PROHIBITION, "", 1)
                self.assertNotRegex(
                    content,
                    re.compile(r"\b(?:ECG|PPG|clinical waveform(?:s)?|raw ECG|raw PPG)\b", re.IGNORECASE),
                )


if __name__ == "__main__":
    unittest.main()

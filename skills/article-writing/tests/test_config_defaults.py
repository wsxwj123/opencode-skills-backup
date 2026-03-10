import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CONFIG_MANAGER_PATH = SKILL_ROOT / "scripts" / "config_manager.py"
PROJECT_INIT_PATH = SKILL_ROOT / "templates" / "project_init.json"
REVIEWER_CONCERNS_PATH = SKILL_ROOT / "templates" / "reviewer_concerns.json"


def load_config_manager_module():
    spec = importlib.util.spec_from_file_location("article_config_manager", CONFIG_MANAGER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ConfigDefaultsTests(unittest.TestCase):
    def test_project_template_defaults_to_drug_delivery(self):
        template = json.loads(PROJECT_INIT_PATH.read_text(encoding="utf-8"))
        project_config = template["project_config_template"]
        self.assertEqual(project_config["field_config"], "drug_delivery")
        self.assertEqual(project_config["research_field"], "Drug Delivery System")

    def test_config_manager_default_field_is_drug_delivery(self):
        module = load_config_manager_module()
        self.assertEqual(module.FieldConfigManager.DEFAULT_FIELD, "drug_delivery")

    def test_reviewer_template_preserves_drug_delivery_detail(self):
        reviewer_concerns = json.loads(REVIEWER_CONCERNS_PATH.read_text(encoding="utf-8"))
        self.assertIn("Nanocarrier", reviewer_concerns["concerns_by_system"])
        self.assertIn("EPR_controversy", reviewer_concerns["mitigation_strategies"])


if __name__ == "__main__":
    unittest.main()

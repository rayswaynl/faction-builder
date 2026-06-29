"""
Tests for gen_unit_catalog.py parsers.
Run: python -m unittest test_gen_unit_catalog -v
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from gen_unit_catalog import classify, parse_cfg_vehicles


class TestClassify(unittest.TestCase):
    """Unit-type classification via parent chain walking."""

    # Minimal parent map simulating CfgVehicles hierarchy
    PARENT_MAP = {
        # Man branch
        "GUE_Soldier_Base": "Man",
        "GUE_Soldier_1": "GUE_Soldier_Base",
        "GUE_Soldier_CO": "GUE_Soldier_Base",
        # Car branch
        "TT650_Gue": "Motorcycle",
        "V3S_Gue": "Truck",
        "Offroad_DSHKM_Gue": "Car",
        # Tank branch
        "T72_Gue": "Tank",
        "BMP2_Gue": "APC_tracked",
        "BRDM2_Gue": "Wheeled_APC",
        # Air branch
        "Mi17_Civilian": "Helicopter",
        "An2_1_TK_CIV_EP1": "Plane",
        # Static branch
        "GUE_WarfareBMGNest_PK": "Static",
        "DSHKM_Gue": "Static",
    }

    def test_man(self):
        self.assertEqual(classify("GUE_Soldier_1", self.PARENT_MAP), "man")

    def test_man_deep(self):
        # Two levels of inheritance to Man
        self.assertEqual(classify("GUE_Soldier_CO", self.PARENT_MAP), "man")

    def test_car_motorcycle(self):
        self.assertEqual(classify("TT650_Gue", self.PARENT_MAP), "car")

    def test_car_truck(self):
        self.assertEqual(classify("V3S_Gue", self.PARENT_MAP), "car")

    def test_car_offroad(self):
        self.assertEqual(classify("Offroad_DSHKM_Gue", self.PARENT_MAP), "car")

    def test_tank(self):
        self.assertEqual(classify("T72_Gue", self.PARENT_MAP), "tank")

    def test_apc_tracked(self):
        self.assertEqual(classify("BMP2_Gue", self.PARENT_MAP), "tank")

    def test_wheeled_apc(self):
        self.assertEqual(classify("BRDM2_Gue", self.PARENT_MAP), "tank")

    def test_helicopter(self):
        self.assertEqual(classify("Mi17_Civilian", self.PARENT_MAP), "air")

    def test_plane(self):
        self.assertEqual(classify("An2_1_TK_CIV_EP1", self.PARENT_MAP), "air")

    def test_static(self):
        self.assertEqual(classify("GUE_WarfareBMGNest_PK", self.PARENT_MAP), "static")

    def test_static_gun(self):
        self.assertEqual(classify("DSHKM_Gue", self.PARENT_MAP), "static")

    def test_unknown_class_returns_other(self):
        self.assertEqual(classify("SomeRandomClass", self.PARENT_MAP), "other")

    def test_class_with_no_parent(self):
        # A root anchor (e.g. "Man") that has no parent
        pm = {"GUE_Soldier_1": "Man"}
        self.assertEqual(classify("GUE_Soldier_1", pm), "man")

    def test_cycle_protection(self):
        # Simulate a pathological cycle — should not infinite-loop
        pm = {"A": "B", "B": "A"}
        result = classify("A", pm)
        self.assertEqual(result, "other")


class TestParseCfgVehiclesFixture(unittest.TestCase):
    """Parse a small CfgVehicles.txt snippet via parse_cfg_vehicles."""

    FIXTURE_TEXT = """class CfgVehicles
{
\tclass All
\t{
\t\tscope = 0;
\t\tdisplayName = "Unknown";
\t};
\tclass Man : Land
\t{
\t\tscope = 0;
\t\tdisplayName = "Man base";
\t};
\tclass GUE_Soldier_Base : Man
\t{
\t\tscope = 0;
\t\tdisplayName = "Guerrilla soldier base";
\t};
\tclass GUE_Soldier_1 : GUE_Soldier_Base
\t{
\t\tscope = 2;
\t\tdisplayName = "Rifleman (AKSU)";
\t};
\tclass T72_Gue : Tank
\t{
\t\tscope = 2;
\t\tdisplayName = "T-72 (GUE)";
\t};
\tclass HiddenClass : All
\t{
\t\tscope = 1;
\t\tdisplayName = "Should not appear";
\t};
};
"""

    def setUp(self):
        # Write fixture to a temp file
        import tempfile
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        self.tmp.write(self.FIXTURE_TEXT)
        self.tmp.close()
        self.parent_map, self.entries = parse_cfg_vehicles(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_scope2_only(self):
        """Only scope=2 classes appear in entries."""
        self.assertIn("GUE_Soldier_1", self.entries)
        self.assertIn("T72_Gue", self.entries)
        self.assertNotIn("HiddenClass", self.entries)
        self.assertNotIn("GUE_Soldier_Base", self.entries)
        self.assertNotIn("Man", self.entries)

    def test_display_name(self):
        self.assertEqual(
            self.entries["GUE_Soldier_1"]["displayName"], "Rifleman (AKSU)"
        )
        self.assertEqual(self.entries["T72_Gue"]["displayName"], "T-72 (GUE)")

    def test_parent_map(self):
        self.assertEqual(self.parent_map.get("GUE_Soldier_1"), "GUE_Soldier_Base")
        self.assertEqual(self.parent_map.get("GUE_Soldier_Base"), "Man")
        self.assertEqual(self.parent_map.get("T72_Gue"), "Tank")

    def test_classify_soldier(self):
        unit_type = classify("GUE_Soldier_1", self.parent_map)
        self.assertEqual(unit_type, "man")

    def test_classify_tank(self):
        unit_type = classify("T72_Gue", self.parent_map)
        self.assertEqual(unit_type, "tank")


class TestCfgVehiclesIntegration(unittest.TestCase):
    """Integration test against the real CfgVehicles.txt (skipped if absent)."""

    CFG_PATH = r"C:\Users\Steff\arma2-co-config-reference\Config\CfgVehicles.txt"

    def setUp(self):
        if not os.path.exists(self.CFG_PATH):
            self.skipTest("CfgVehicles.txt not found — skipping integration test")
        self.parent_map, self.entries = parse_cfg_vehicles(self.CFG_PATH)

    def test_gue_soldier_present(self):
        self.assertIn("GUE_Soldier_1", self.entries)

    def test_gue_soldier_displayname(self):
        entry = self.entries["GUE_Soldier_1"]
        self.assertIn("Rifleman", entry["displayName"])

    def test_gue_soldier_classified_as_man(self):
        unit_type = classify("GUE_Soldier_1", self.parent_map)
        self.assertEqual(unit_type, "man")

    def test_t72_classified_as_tank(self):
        if "T72_Gue" not in self.entries:
            self.skipTest("T72_Gue not found in entries")
        unit_type = classify("T72_Gue", self.parent_map)
        self.assertEqual(unit_type, "tank")

    def test_mi17_classified_as_air(self):
        if "Mi17_Civilian" not in self.entries:
            self.skipTest("Mi17_Civilian not found in entries")
        unit_type = classify("Mi17_Civilian", self.parent_map)
        self.assertEqual(unit_type, "air")

    def test_dshkm_classified_as_static(self):
        if "DSHKM_Gue" not in self.entries:
            self.skipTest("DSHKM_Gue not found in entries")
        unit_type = classify("DSHKM_Gue", self.parent_map)
        self.assertEqual(unit_type, "static")

    def test_minimum_scope2_count(self):
        self.assertGreater(len(self.entries), 100)


if __name__ == "__main__":
    unittest.main()

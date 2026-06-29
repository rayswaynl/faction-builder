"""
Tests for extract_faction_template.py parsers.
Run: python -m unittest test_extract_faction_template -v
"""

import unittest
import sys
import os

# Allow importing from same dir
sys.path.insert(0, os.path.dirname(__file__))

from extract_faction_template import (
    parse_root_vars,
    parse_core_rows,
    parse_registration,
    parse_structures,
    collect_flags,
    _BUILDING_KEYS,
)


class TestParseRootVars(unittest.TestCase):
    """Parse WFBE_%1KEY setVariable lines from Root_GUE.sqf."""

    FIXTURE = r"""
Private ["_side"];
_side = "GUER";

missionNamespace setVariable [Format["WFBE_%1CREW", _side], 'GUE_Soldier_Crew'];
missionNamespace setVariable [Format["WFBE_%1PILOT", _side], 'GUE_Soldier_1'];
missionNamespace setVariable [Format["WFBE_%1FLAG", _side], '\ca\data\Flag_napa_co.paa'];
missionNamespace setVariable [Format["WFBE_%1AMBULANCES", _side], ['V3S_TK_GUE_EP1','V3S_Gue']];
missionNamespace setVariable [Format["WFBE_%1REPAIRTRUCKS", _side], ['WarfareRepairTruck_Gue','V3S_Repair_TK_GUE_EP1']];
missionNamespace setVariable [Format["WFBE_%1DEFAULTFACTION", _side], 'Guerilla'];
"""

    def test_flag_value(self):
        vars_ = parse_root_vars(self.FIXTURE)
        self.assertIn("FLAG", vars_)
        self.assertEqual(vars_["FLAG"], r"'\ca\data\Flag_napa_co.paa'")

    def test_crew_value(self):
        vars_ = parse_root_vars(self.FIXTURE)
        self.assertIn("CREW", vars_)
        self.assertIn("GUE_Soldier_Crew", vars_["CREW"])

    def test_pilot_value(self):
        vars_ = parse_root_vars(self.FIXTURE)
        self.assertIn("PILOT", vars_)
        self.assertIn("GUE_Soldier_1", vars_["PILOT"])

    def test_defaultfaction(self):
        vars_ = parse_root_vars(self.FIXTURE)
        self.assertIn("DEFAULTFACTION", vars_)
        self.assertIn("Guerilla", vars_["DEFAULTFACTION"])

    def test_array_value(self):
        vars_ = parse_root_vars(self.FIXTURE)
        self.assertIn("AMBULANCES", vars_)
        # Should capture the array bracket expression
        self.assertTrue(vars_["AMBULANCES"].startswith("["))

    def test_multiple_vars(self):
        vars_ = parse_root_vars(self.FIXTURE)
        self.assertGreaterEqual(len(vars_), 5)


class TestParseCoreRows(unittest.TestCase):
    """Parse _c/_i paired rows from Core_GUE.sqf."""

    FIXTURE = r"""
Private ['_c','_i'];
_c = [];
_i = [];

/* Infantry */
_c = _c + ['GUE_Soldier_1'];
_i = _i + [['','',150,4,-1,0,0,1,'Guerilla',[]]];

_c = _c + ['GUE_Soldier_AT'];
_i = _i + [['','',220,5,-1,1,0,1,'Guerilla',[]]];

/* Light Vehicles */
_c = _c + ['TT650_Gue'];
_i = _i + [['','',150,15,-2,0,1,0,'Guerilla',[]]];

/* Static Defenses */
_c = _c + ['GUE_WarfareBMGNest_PK'];
_i = _i + [['','',300,0,1,0,'Defense',0,'Guerilla',[]]];
"""

    def test_count(self):
        rows = parse_core_rows(self.FIXTURE)
        self.assertEqual(len(rows), 4)

    def test_first_classname(self):
        rows = parse_core_rows(self.FIXTURE)
        self.assertEqual(rows[0]["classname"], "GUE_Soldier_1")

    def test_vehicle_classname(self):
        rows = parse_core_rows(self.FIXTURE)
        vehicle_row = next(r for r in rows if r["classname"] == "TT650_Gue")
        self.assertIsNotNone(vehicle_row)

    def test_static_classname(self):
        rows = parse_core_rows(self.FIXTURE)
        static_row = next(r for r in rows if r["classname"] == "GUE_WarfareBMGNest_PK")
        self.assertIsNotNone(static_row)

    def test_tuple_captured(self):
        rows = parse_core_rows(self.FIXTURE)
        # Tuple should be a non-empty bracket expression
        self.assertTrue(rows[0]["raw_tuple"].startswith("["))
        self.assertIn("150", rows[0]["raw_tuple"])

    def test_infantry_factory_code(self):
        """Infantry rows have -1 in tuple position 4."""
        rows = parse_core_rows(self.FIXTURE)
        inf = rows[0]
        self.assertIn("-1", inf["raw_tuple"])

    def test_vehicle_factory_code(self):
        """Vehicle rows have -2 in tuple position 4."""
        rows = parse_core_rows(self.FIXTURE)
        veh = next(r for r in rows if r["classname"] == "TT650_Gue")
        self.assertIn("-2", veh["raw_tuple"])


class TestParseRegistration(unittest.TestCase):
    """Parse WFBE_C_UNITS_FACTIONS_* arrays from Init_CommonConstants.sqf."""

    FIXTURE = r"""
switch (true) do {
    case (WF_A2_CombinedOps): {
        WFBE_C_UNITS_FACTIONS_EAST = ['INS','RU','TKA'];
        WFBE_C_UNITS_FACTIONS_GUER = ['GUE','PMC','TKGUE'];
        WFBE_C_UNITS_FACTIONS_WEST = ['CDF','US','USMC'];

        missionNamespace setVariable ['WFBE_C_UNITS_FACTION_WEST', 2];
        missionNamespace setVariable ['WFBE_C_UNITS_FACTION_EAST', 1];
        missionNamespace setVariable ['WFBE_C_UNITS_FACTION_GUER', 0];
    };
};
"""

    def test_factions_guer(self):
        reg = parse_registration(self.FIXTURE)
        self.assertIn("factions_guer", reg)
        self.assertIn("GUE", reg["factions_guer"])
        self.assertIn("PMC", reg["factions_guer"])
        self.assertIn("TKGUE", reg["factions_guer"])

    def test_factions_west(self):
        reg = parse_registration(self.FIXTURE)
        self.assertIn("factions_west", reg)
        self.assertIn("CDF", reg["factions_west"])
        self.assertIn("US", reg["factions_west"])
        self.assertIn("USMC", reg["factions_west"])

    def test_factions_east(self):
        reg = parse_registration(self.FIXTURE)
        self.assertIn("factions_east", reg)
        self.assertIn("INS", reg["factions_east"])
        self.assertIn("RU", reg["factions_east"])

    def test_indices(self):
        reg = parse_registration(self.FIXTURE)
        self.assertIn("index_west", reg)
        self.assertEqual(reg["index_west"], 2)
        self.assertEqual(reg["index_east"], 1)
        self.assertEqual(reg["index_guer"], 0)


class TestParseStructures(unittest.TestCase):
    """Parse building classnames, costs, times from Structures_GUE.sqf."""

    FIXTURE = r"""
Private ['_c','_count','_d','_dir','_dis','_n','_s','_side','_t','_v'];

_side = _this;

_MHQ = "BRDM2_HQ_Gue";
_HQ = "BRDM2_HQ_Gue_unfolded";
_BAR = "Gue_WarfareBBarracks";
_LVF = "Gue_WarfareBLightFactory";
_CC = "GUE_WarfareBUAVterminal";
_HEAVY = "Gue_WarfareBHeavyFactory";
_AIR = "GUE_WarfareBAircraftFactory";
_SP = "GUE_WarfareBVehicleServicePoint";
_AAR = "Gue_WarfareBAntiAirRadar";

missionNamespace setVariable [Format["WFBE_%1CONSTRUCTIONSITE", _side], 'Gue_WarfareBContructionSite'];

_v   = ["Headquarters"];
_n   = [_HQ];
_d   = [getText (configFile >> "CfgVehicles" >> (_n select (count _n - 1)) >> "displayName")];
_c   = [missionNamespace getVariable "WFBE_C_STRUCTURES_HQ_COST_DEPLOY"];
_t   = [if (WF_Debug) then {1} else {30}];
_s   = ["HQSite"];
_dis = [15];
_dir = [0];

_v = _v + ["Barracks"];
_n = _n + [_BAR];
_c = _c + [200];
_t = _t + [if (WF_Debug) then {1} else {70}];

_v = _v + ["Light"];
_n = _n + [_LVF];
_c = _c + [600];
_t = _t + [if (WF_Debug) then {1} else {90}];

_v = _v + ["CommandCenter"];
_n = _n + [_CC];
_c = _c + [1200];
_t = _t + [if (WF_Debug) then {1} else {110}];

_v = _v + ["Heavy"];
_n = _n + [_HEAVY];
_c = _c + [2800];
_t = _t + [if (WF_Debug) then {1} else {130}];

_v = _v + ["Aircraft"];
_n = _n + [_AIR];
_c = _c + [4400];
_t = _t + [if (WF_Debug) then {1} else {150}];

_v = _v + ["ServicePoint"];
_n = _n + [_SP];
_c = _c + [700];
_t = _t + [if (WF_Debug) then {1} else {70}];

_v = _v + ["AARadar"];
_n = _n + [_AAR];
_c = _c + [3200];
_t = _t + [if (WF_Debug) then {1} else {280}];

missionNamespace setVariable [Format["WFBE_%1MHQNAME", _side], _MHQ];
missionNamespace setVariable [Format["WFBE_%1STRUCTURES", _side], _v];
missionNamespace setVariable [Format["WFBE_%1STRUCTURECOSTS", _side], _c];
missionNamespace setVariable [Format["WFBE_%1STRUCTURETIMES", _side], _t];

/* Defenses */
_n   = ["GUE_WarfareBMGNest_PK"];
_n = _n + ["DSHKM_Gue"];

missionNamespace setVariable [Format["WFBE_%1DEFENSENAMES", _side], _n];
"""

    def test_mhq_classname(self):
        s = parse_structures(self.FIXTURE)
        self.assertEqual(s["mhq"], "BRDM2_HQ_Gue")

    def test_eight_buildings(self):
        s = parse_structures(self.FIXTURE)
        self.assertEqual(len(s["buildings"]), 8)

    def test_building_keys(self):
        s = parse_structures(self.FIXTURE)
        keys = [b["key"] for b in s["buildings"]]
        self.assertEqual(keys, _BUILDING_KEYS)

    def test_barracks_cost(self):
        s = parse_structures(self.FIXTURE)
        barracks = next(b for b in s["buildings"] if b["key"] == "Barracks")
        self.assertEqual(barracks["cost"], 200)

    def test_aircraft_time(self):
        s = parse_structures(self.FIXTURE)
        aircraft = next(b for b in s["buildings"] if b["key"] == "Aircraft")
        self.assertEqual(aircraft["time"], 150)

    def test_aaradar_cost(self):
        s = parse_structures(self.FIXTURE)
        aaradar = next(b for b in s["buildings"] if b["key"] == "AARadar")
        self.assertEqual(aaradar["cost"], 3200)

    def test_defense_names(self):
        s = parse_structures(self.FIXTURE)
        self.assertIn("GUE_WarfareBMGNest_PK", s["defense_names"])
        self.assertIn("DSHKM_Gue", s["defense_names"])


class TestCollectFlags(unittest.TestCase):
    """Test that collect_flags returns GUE flag correctly (requires source files)."""

    def test_gue_flag_present(self):
        flags = collect_flags()
        if not flags:
            self.skipTest("Source Root_*.sqf files not accessible")
        gue = next((f for f in flags if f["faction"] == "GUE"), None)
        self.assertIsNotNone(gue, "GUE faction must be in flags list")
        self.assertEqual(gue["paa"], r"\ca\data\Flag_napa_co.paa")

    def test_minimum_flag_count(self):
        flags = collect_flags()
        if not flags:
            self.skipTest("Source Root_*.sqf files not accessible")
        self.assertGreaterEqual(len(flags), 8)


if __name__ == "__main__":
    unittest.main()

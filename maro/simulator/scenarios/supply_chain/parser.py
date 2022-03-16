# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import collections
import os
from dataclasses import dataclass
from importlib import import_module
from typing import Dict, Optional

import pandas as pd
from yaml import safe_load


@dataclass
class ModuleDef:
    alias: str
    module_path: str
    class_name: str
    class_type: type


@dataclass
class DataModelDef(ModuleDef):
    name_in_frame: str


@dataclass
class EntityDef(ModuleDef):
    data_model_alias: str


@dataclass
class UnitDef(EntityDef):
    pass


@dataclass
class FacilityDef(EntityDef):
    pass


def find_class_type(module_path: str, class_name: str) -> type:
    """Find class type by module path and class name.

    Args:
        module_path (str): Full path of the module.
        class_name (str): Class name to find.

    Returns:
        type: Type of specified class.
    """
    target_module = import_module(module_path)

    return getattr(target_module, class_name)


def copy_dict(target: dict, source: dict) -> None:
    """Copy values from source to target dict.

    Args:
        target (dict): Target dictionary to copy to.
        source (dict): Source dictionary to copy from.
    """
    for k, v in source.items():
        if type(v) != dict:
            target[k] = v
        else:
            if k not in target:
                target[k] = {}

            copy_dict(target[k], v)


class SupplyChainConfiguration:
    """Configuration of supply chain scenario."""

    def __init__(self) -> None:
        # Data model definitions.
        self.data_model_defs: Dict[str, DataModelDef] = {}

        # Unit definitions.
        self.unit_defs: Dict[str, UnitDef] = {}

        # Facility definitions.
        self.facility_defs: Dict[str, FacilityDef] = {}

        # World configurations.
        self.world = {}

        # Other settings.
        self.settings = {}

    def add_data_definition(self, alias: str, class_name: str, module_path: str, name_in_frame: str) -> None:
        """Add a data model definition.

        Args:
            alias (str): Alias of this data model.
            class_name (str): Name of class.
            module_path (str): Full path of module.
            name_in_frame (str): Data model name in frame.
        """
        # Check conflicting.
        assert alias not in self.data_model_defs

        self.data_model_defs[alias] = DataModelDef(
            alias,
            module_path,
            class_name,
            find_class_type(module_path, class_name),
            name_in_frame,
        )

    def add_unit_definition(self, alias: str, class_name: str, module_path: str, data_model: str) -> None:
        """Add unit definition.

        Args:
            alias (str): Alias of this data model.
            class_name (str): Name of class.
            module_path (str): Full path of module.
            data_model (str): Data model used for this unit.
        """
        assert alias not in self.unit_defs

        self.unit_defs[alias] = UnitDef(
            alias,
            module_path,
            class_name,
            find_class_type(module_path, class_name),
            data_model,
        )

    def add_facility_definition(self, alias: str, class_name: str, module_path: str, data_model_alias: str) -> None:
        """Add a facility definition.

        Args:
            alias (str): Alias of this facility.
            class_name (str): Name of this class.
            module_path (str): Full path of the module.
            data_model_alias (str): Data model alias.
        """
        assert alias not in self.facility_defs

        self.facility_defs[alias] = FacilityDef(
            alias,
            module_path,
            class_name,
            find_class_type(module_path, class_name),
            data_model_alias,
        )


class ConfigParser:
    """Supply chain configuration parser."""

    def __init__(self, core_path: str, config_path: str) -> None:
        self._result: Optional[SupplyChainConfiguration] = None

        self._core_path = core_path
        self._config_path = config_path

    def parse(self) -> SupplyChainConfiguration:
        """Parse configuration of current scenario.

        Returns:
            SupplyChainConfiguration: Configuration result of this scenario.
        """
        if self._result is None:
            self._result = SupplyChainConfiguration()
            self._parse_core()
            self._parse_config()

        return self._result

    def _parse_core(self) -> None:
        """Parse configuration from core.yml."""
        with open(self._core_path, "rt") as fp:
            conf = safe_load(fp)

            self._parse_core_conf(conf)

    def _parse_core_conf(self, conf: dict) -> None:
        # Data models.
        if "datamodels" in conf:
            for module_conf in conf["datamodels"]["modules"]:
                module_path = module_conf["path"]

                for class_alias, class_def in module_conf["definitions"].items():
                    self._result.add_data_definition(
                        class_alias,
                        class_def["class"],
                        module_path,
                        class_def["name_in_frame"],
                    )

        # TODO: dup code
        # Units.
        if "units" in conf:
            for module_conf in conf["units"]["modules"]:
                module_path = module_conf["path"]

                for class_alias, class_def in module_conf["definitions"].items():
                    # children not in unit definition
                    self._result.add_unit_definition(
                        class_alias,
                        class_def["class"],
                        module_path,
                        class_def.get("datamodel", None),
                    )

        # Facilities.
        if "facilities" in conf:
            for module_conf in conf["facilities"]["modules"]:
                module_path = module_conf["path"]

                for class_alias, class_def in module_conf["definitions"].items():
                    self._result.add_facility_definition(
                        class_alias,
                        class_def["class"],
                        module_path,
                        class_def.get("datamodel", None),
                    )

    def _parse_config(self) -> None:
        """Parse configurations."""
        with open(os.path.join(self._config_path, "config.yml"), "rt") as fp:
            conf = safe_load(fp)

            # Read customized core part.
            customized_core_conf = conf.get("core", None)

            if customized_core_conf is not None:
                self._parse_core_conf(customized_core_conf)

            # Facility definitions is not required, but it would be much simple to config with it
            facility_definitions = conf.get("facility_definitions", {})
            world_def = conf["world"]

            # Go through world configurations to generate a full one.
            # . Copy other configurations first
            for sub_conf_name in ("skus", "topology", "grid"):
                self._result.world[sub_conf_name] = world_def[sub_conf_name]

            # . Copy facilities content different if without definition reference.
            # or copy from definition first, then override with current.
            self._result.world["facilities"] = []

            for facility_conf in world_def["facilities"]:
                facility_ref = facility_conf.get("definition_ref", None)

                facility = {}

                if facility_ref is not None:
                    # Copy definition from base.
                    copy_dict(facility, facility_definitions[facility_ref])

                # Override with current.
                copy_dict(facility, facility_conf)

                self._result.world["facilities"].append(facility)

            self._result.settings = conf.get("settings", {})

        # Parse demands from files if exist
        self._result.world["demands"] = {}
        for facility in self._result.world["facilities"]:
            facility_name = facility["name"]
            demand_file_path = os.path.join(self._config_path, f"demand__{facility_name}.csv")
            demand_dict = collections.defaultdict(dict)
            if os.path.exists(demand_file_path):
                df = pd.read_csv(demand_file_path)
                for _, row in df.iterrows():
                    tick, sku_id, demand = row
                    demand_dict[sku_id][tick] = demand
                self._result.world["demands"][facility_name] = dict(demand_dict)

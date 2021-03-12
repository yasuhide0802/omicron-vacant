# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import io
import yaml
import unittest

from maro.simulator import Env
from maro.utils import convert_dottable
from maro.data_lib import BinaryConverter
from maro.event_buffer import EventBuffer
from maro.simulator.scenarios.vm_scheduling import CpuReader
from maro.simulator.scenarios.vm_scheduling import AllocateAction, PostponeAction
from maro.simulator.scenarios.vm_scheduling.business_engine import VmSchedulingBusinessEngine


class TestCpuReader(unittest.TestCase):
    for i in range(1, 4):
        meta_file = "tests/data/vm_scheduling/cpu_readings.yml"
        bin_file_name = f"tests/data/vm_scheduling/vm_cpu_readings-file-{i}-of-test.bin"
        csv_file = f"tests/data/vm_scheduling/vm_cpu_readings-file-{i}-of-test.csv"

        converter = BinaryConverter(bin_file_name, meta_file)
        converter.add_csv(csv_file)
        converter.flush()

    data_path = "tests/data/vm_scheduling/vm_cpu_readings-file-1-of-test.bin"

    def setUp(self):
        self.cpu_reader = CpuReader(self.data_path, 0)

    def tearDown(self):
        self.cpu_reader.reset()

    def test_first_file_first_tick(self):
        cpu_utilization_dict = self.cpu_reader.items(tick=0)
        expected = 4
        self.assertEqual(expected, len(cpu_utilization_dict))

    def test_first_file_last_tick(self):
        cpu_utilization_dict = self.cpu_reader.items(tick=1)
        expected = 13
        self.assertEqual(expected, len(cpu_utilization_dict))

    def test_switch_file(self):
        cpu_utilization_dict = self.cpu_reader.items(tick=1)
        cpu_utilization_dict = self.cpu_reader.items(tick=2)
        expected = 8
        self.assertEqual(expected, len(cpu_utilization_dict))

    def test_last_file(self):
        cpu_utilization_dict = {}
        for i in range(3):
            cpu_utilization_dict = self.cpu_reader.items(tick=i)

        expected = 8
        self.assertEqual(expected, len(cpu_utilization_dict))

        cpu_utilization_dict = self.cpu_reader.items(tick=3)
        expected = 7
        self.assertEqual(expected, len(cpu_utilization_dict))

    def test_reset(self):
        self.cpu_reader.items(tick=0)
        self.cpu_reader.items(tick=1)
        self.cpu_reader.items(tick=2)
        self.cpu_reader.items(tick=3)

        self.cpu_reader.reset()

        cpu_utilization_dict = self.cpu_reader.items(tick=0)
        expected = 4
        self.assertEqual(expected, len(cpu_utilization_dict))

        cpu_utilization_dict = self.cpu_reader.items(tick=1)
        expected = 13
        self.assertEqual(expected, len(cpu_utilization_dict))

        cpu_utilization_dict = self.cpu_reader.items(tick=2)
        expected = 8
        self.assertEqual(expected, len(cpu_utilization_dict))

    def test_start_tick_not_in_first_file(self):
        self.cpu_reader = CpuReader(self.data_path, 2)

        cpu_utilization_dict = self.cpu_reader.items(tick=2)
        expected = 8
        self.assertEqual(expected, len(cpu_utilization_dict))

        cpu_utilization_dict = self.cpu_reader.items(tick=3)
        expected = 7
        self.assertEqual(expected, len(cpu_utilization_dict))


class TestRegion(unittest.TestCase):

    def setUp(self):
        config_path = "tests/data/vm_scheduling"
        self.eb = EventBuffer()
        self.be = VmSchedulingBusinessEngine(
            event_buffer=self.eb, topology=config_path, start_tick=0, max_tick=3,
            snapshot_resolution=1, max_snapshots=None, additional_options={}
        )

    def test_config(self):
        region_amount = self.be._region_amount
        expected = 2
        self.assertEqual(expected, region_amount)

        zone_amount = self.be._zone_amount
        expected = 2
        self.assertEqual(expected, zone_amount)

        data_center_amount = self.be._data_center_amount
        expected = 3
        self.assertEqual(expected, data_center_amount)

        cluster_amount = self.be._cluster_amount
        expected = 8
        self.assertEqual(expected, cluster_amount)

        rack_amount = self.be._rack_amount
        expected = 75
        self.assertEqual(expected, rack_amount)

        pm_amount = self.be._pm_amount
        expected = 1130
        self.assertEqual(expected, pm_amount)


class TestPriceModel(unittest.TestCase):

    def setUp(self):
        config_path = "tests/data/vm_scheduling/env_config.yml"
        with io.open(config_path, "r") as in_file:
            raw_config = yaml.safe_load(in_file)
            config = convert_dottable(raw_config)
        env = Env(
            scenario=config.env.scenario,
            topology=config.env.topology,
            start_tick=config.env.start_tick,
            durations=config.env.durations,
            snapshot_resolution=config.env.resolution
        )
        metrics, decision_event, is_done = env.step(None)
        action = AllocateAction(
            vm_id=decision_event.vm_id,
            pm_id=decision_event.valid_pms[0]
        )
        self.metrics, decision_event, is_done = env.step(action)

    def test_price(self):
        total_incomes = self.metrics['total_incomes']
        expected = 0.067
        self.assertLess(abs(expected - total_incomes), 0.01)

        energy_consumption_cost = self.metrics['energy_consumption_cost']
        expected = 0.238
        self.assertLess(abs(expected - energy_consumption_cost), 0.01)

        total_profit = self.metrics['total_profit']
        expected = -0.17
        self.assertLess(abs(expected - total_profit), 0.01)


if __name__ == "__main__":
    unittest.main()

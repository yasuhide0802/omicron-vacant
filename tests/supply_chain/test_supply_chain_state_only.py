import os
import unittest
import numpy as np

from maro.simulator import Env
from maro.simulator.scenarios.supply_chain import FacilityBase, ConsumerAction, StorageUnit
from maro.simulator.scenarios.supply_chain.business_engine import SupplyChainBusinessEngine
from maro.simulator.scenarios.supply_chain.order import Order
from maro.simulator.scenarios.supply_chain.sku_dynamics_sampler import OneTimeSkuPriceDemandSampler, \
    DataFileDemandSampler


def build_env(case_name: str, durations: int):
    case_folder = os.path.join("tests", "data", "supply_chain", case_name)

    env = Env(scenario="supply_chain", topology=case_folder, durations=durations)

    return env


def get_product_dict_from_storage(env: Env, frame_index: int, node_index: int):
    product_list = env.snapshot_list["storage"][frame_index:node_index:"product_list"].flatten().astype(np.int)
    product_quantity = env.snapshot_list["storage"][frame_index:node_index:"product_quantity"].flatten().astype(np.int)

    return {product_id: quantity for product_id, quantity in zip(product_list, product_quantity)}


SKU1_ID = 1
SKU2_ID = 2
SKU3_ID = 3
SKU4_ID = 4
FOOD_1_ID = 20
HOBBY_1_ID = 30


class MyTestCase(unittest.TestCase):
    """
        state only  test:
        . consumer_state_only
            . "pending_order_daily"
        . seller_state_only
            . "sale_mean"
            . "sale_hist"
        . distribution_state_only
            . "pending_order"
            . "in_transit_orders"
    """

    def test_consumer_state_only(self) -> None:
        """Test the "pending_order_daily" of the consumer unit when vlt is less than "pending_order_daily" length."""
        env = build_env("case_05", 100)
        be = env.business_engine
        assert isinstance(be, SupplyChainBusinessEngine)

        supplier_3 = be.world._get_facility_by_name("Supplier_SKU3")
        warehouse_1 = be.world._get_facility_by_name("Warehouse_001")
        distribution_unit = supplier_3.distribution

        order_1 = Order(warehouse_1, SKU3_ID, 1, "train")
        order_2 = Order(warehouse_1, SKU3_ID, 2, "train")
        order_3 = Order(warehouse_1, SKU3_ID, 3, "train")
        consumer_unit = warehouse_1.products[SKU3_ID].consumer
        env.step(None)

        #  vlt is greater than len(pending_order_len), which will cause the pending order to increase
        consumer_unit._update_open_orders(warehouse_1.id, SKU3_ID, 1)
        distribution_unit.place_order(order_1)
        self.assertEqual(1, len(distribution_unit._order_queues["train"]))
        self.assertEqual(1, sum([order.quantity for order in distribution_unit._order_queues["train"]]))
        self.assertEqual(0 * 1, distribution_unit.transportation_cost[SKU3_ID])

        supplier_3_id = 1

        env.step(None)
        # Here the vlt of "train" is less than "pending_order_daily" length
        self.assertEqual([0, 0, 1, 0],  list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))
        self.assertEqual(1 * 1, distribution_unit.transportation_cost[SKU3_ID])

        # add another order, it would be successfully scheduled.
        consumer_unit._update_open_orders(warehouse_1.id, SKU3_ID, 2)
        distribution_unit.place_order(order_2)
        self.assertEqual(1, len(distribution_unit._order_queues["train"]))
        self.assertEqual(2, sum([order.quantity for order in distribution_unit._order_queues["train"]]))

        self.assertEqual([0, 0,  1, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        start_tick = env.tick
        expected_tick = start_tick + 3

        # vlt is greater than len(pending_order_len), which will cause the pending order to increase.
        # Add another order, which will be successfully arranged, but there are no extra vehicles now.
        consumer_unit._update_open_orders(warehouse_1.id, SKU3_ID, 3)
        distribution_unit.place_order(order_3)

        self.assertEqual(2, len(distribution_unit._order_queues["train"]))
        self.assertEqual(5, sum([order.quantity for order in distribution_unit._order_queues["train"]]))
        # For the third order, there are two trains in total, sqo the third order will not enter pending_order_daily after the step

        env.step(None)
        self.assertEqual([0, 1, 2, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))
        self.assertEqual(1 * (1+2), distribution_unit.transportation_cost[SKU3_ID])

        env.step(None)
        self.assertEqual([1, 2, 0, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        self.assertEqual(1, len(distribution_unit._order_queues["train"]))
        self.assertEqual(3, sum([order.quantity for order in distribution_unit._order_queues["train"]]))

        self.assertEqual(1 * (1+2), distribution_unit.transportation_cost[SKU3_ID])

        env.step(None)
        self.assertEqual([2, 0, 0, 3], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        # will arrive at the end of this tick, still on the way.
        self.assertEqual(0, len(distribution_unit._order_queues["train"]))
        self.assertEqual(0, sum([order.quantity for order in distribution_unit._order_queues["train"]]))

        self.assertEqual(1 * (2+3), distribution_unit.transportation_cost[SKU3_ID])
        self.assertEqual(10 * 0, distribution_unit.delay_order_penalty[SKU3_ID])

        assert env.tick == expected_tick
        env.step(None)
        self.assertEqual([0, 0, 3, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        self.assertEqual(0, len(distribution_unit._order_queues["train"]))
        self.assertEqual(0, sum([order.quantity for order in distribution_unit._order_queues["train"]]))

        self.assertEqual(0, distribution_unit.delay_order_penalty[SKU3_ID])
        self.assertEqual(1 * 3, distribution_unit.transportation_cost[SKU3_ID])

        env.step(None)

        consumer_unit._update_open_orders(warehouse_1.id, SKU3_ID, 1)
        distribution_unit.place_order(order_1)

        self.assertEqual([0, 3, 0, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        self.assertEqual(1, len(distribution_unit._order_queues["train"]))
        self.assertEqual(1, sum([order.quantity for order in distribution_unit._order_queues["train"]]))

        self.assertEqual(0, distribution_unit.delay_order_penalty[SKU3_ID])
        self.assertEqual(1 * 3 , distribution_unit.transportation_cost[SKU3_ID])

        env.step(None)

        self.assertEqual(1 * 3 + 1 * 1, distribution_unit.transportation_cost[SKU3_ID])

        self.assertEqual([3, 0, 1, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        start_tick = env.tick
        expected_tick = start_tick + 3 - 1  # vlt = 3
        while env.tick < expected_tick:
            env.step(None)

        self.assertEqual([1, 0, 0, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))
        self.assertEqual(1 * 1 * 1, distribution_unit.transportation_cost[SKU3_ID])

    def test_consumer_vlt_state_only(self) -> None:
        """Tests the "pending_order_daily" of the consumer unit when vlt is greater than the "pending_order_daily length. """

        env = build_env("case_05", 100)
        be = env.business_engine
        assert isinstance(be, SupplyChainBusinessEngine)

        warehouse_1 = be.world._get_facility_by_name("Warehouse_001")
        retailer_1: FacilityBase = be.world._get_facility_by_name("Retailer_001")
        warehouse_1_id, retailer_1_id = 6, 13

        warehouse_1_distribution_unit = warehouse_1.distribution
        self.assertEqual(0, len(warehouse_1_distribution_unit._order_queues["train"]))

        env.step(None)

        order_1 = Order(retailer_1, SKU2_ID, 1, "train")
        consumer_unit = retailer_1.products[SKU2_ID].consumer

        consumer_unit._update_open_orders(retailer_1.id, SKU2_ID, 1)
        warehouse_1_distribution_unit.place_order(order_1)
        # The vlt configuration of this topology is 5.
        self.assertEqual(1, len(warehouse_1_distribution_unit._order_queues["train"]))

        # After env.step runs, where tick is 1. order_1 will arrive at tick=5. order_2 will arrive at tick=6.
        env.step(None)

        self.assertEqual(0, len(warehouse_1_distribution_unit._order_queues["train"]))
        self.assertEqual([0, 0, 0, 1], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([0, 0, 0, 1], list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        order_2 = Order(retailer_1, SKU2_ID, 2, "train")
        consumer_unit._update_open_orders(retailer_1.id, SKU2_ID, 2)
        warehouse_1_distribution_unit.place_order(order_2)

        # The vlt configuration of this topology is 5.
        self.assertEqual(1, len(warehouse_1_distribution_unit._order_queues["train"]))

        # After env.step runs, where tick is 2. order_1 will arrive at tick=5. order_2 will arrive at tick=6.
        env.step(None)

        self.assertEqual([0, 0, 1, 2], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([0, 0, 1, 2], list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        # After env.step runs, where tick is 3. order_1 will arrive at tick=5. order_2 will arrive at tick=6.
        env.step(None)

        self.assertEqual([0, 1, 2, 0], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([0, 1, 2, 0], list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        self.assertEqual(3, env.metrics["facilities"][retailer_1_id]["in_transit_orders"][SKU2_ID])

        # There are a total of two trains in the configuration, and they have all been dispatched now.
        order_3 = Order(retailer_1, SKU2_ID, 3, "train")
        self.assertEqual(0, len(warehouse_1_distribution_unit._order_queues["train"]))
        consumer_unit._update_open_orders(retailer_1.id, SKU2_ID, 3)
        warehouse_1_distribution_unit.place_order(order_3)

        # After env.step runs, where tick is 4. order_1 will arrive at tick=5. order_2 will arrive at tick=6.order_3 is expected to arrive at tick=8 under normal circumstances.
        env.step(None)
        self.assertEqual([1, 2, 0, 0], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([1, 2, 0, 0], list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        self.assertEqual(6, env.metrics["facilities"][retailer_1_id]["in_transit_orders"][SKU2_ID])

        self.assertEqual(0, env.metrics["facilities"][retailer_1_id]["in_transit_orders"][SKU3_ID])

        # After env.step runs, where tick is 5. order_1 arrives after env.step. order_2 will arrive at tick=6.order_3 is expected to arrive at tick=8 under normal circumstances.
        env.step(None)
        self.assertEqual([2, 0, 0, 0], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([2, 0, 0, 0], list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        # After env.step runs, where tick is 6. order_2 arrives after env.step. There are empty cars at this time, order_3 will arrive at tick = 11.
        env.step(None)
        self.assertEqual([0, 0, 0, 0], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([0, 0, 0, 0], list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        # When order_1 arrives at the next step, the in_transit_orders of retailer_1 should be the negative number 1+2+3-1 of the arrival order of retailer_1.
        self.assertEqual(5, env.metrics["facilities"][retailer_1_id]["in_transit_orders"][SKU2_ID])

        # After env.step runs, where tick is 7. order_2 arrives after env.step. There are empty cars at this time, order_3 will arrive at tick = 11.
        env.step(None)

        # When order_2 arrives at the next step, the in_transit_orders of retailer_1 should be the negative number 1+2+3-1-2 of the arrival order of retailer_1.
        self.assertEqual(3, env.metrics["facilities"][retailer_1_id]["in_transit_orders"][SKU2_ID])

        order_4 = Order(retailer_1, SKU2_ID, 4, "train")
        consumer_unit._update_open_orders(retailer_1.id, SKU2_ID, 4)
        warehouse_1_distribution_unit.place_order(order_4)

        # After env.step runs, where tick is 8. order_3 will arrive at tick = 11. order_4 is expected to arrive at tick=12 under normal circumstances.
        env.step(None)
        self.assertEqual([0, 0, 3, 4], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([0, 0, 3, 4],  list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        # After env.step runs, where tick is 9. order_3 will arrive at tick = 11. order_4 is expected to arrive at tick=12 under normal circumstances.
        env.step(None)
        self.assertEqual([0, 3, 4, 0], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([0, 3, 4, 0],  list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        # After env.step runs, where tick is 10. order_3 will arrive at tick = 11. order_4 is expected to arrive at tick=12 under normal circumstances.
        env.step(None)
        self.assertEqual([3, 4, 0, 0], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([3, 4, 0, 0],  list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

        # After env.step runs, where tick is 11. order_3 arrives after env.step. order_4 is expected to arrive at tick=12 under normal circumstances.
        env.step(None)
        self.assertEqual([4, 0, 0, 0], list(env.metrics["facilities"][warehouse_1_id]["pending_order_daily"][SKU2_ID]))
        self.assertEqual([4, 0, 0, 0],  list(warehouse_1_distribution_unit.pending_order_daily(env.tick)[SKU2_ID]))

    def test_seller_state_only(self) -> None:
        """Test "sale_mean" and "_sale_hist """

        env = build_env("case_05", 600)
        be = env.business_engine
        assert isinstance(be, SupplyChainBusinessEngine)
        store_001: FacilityBase = be.world._get_facility_by_name("Store_001")
        storeproductunit_sku1, storeproductunit_sku2, storeproductunit_sku3 = 1, 3, 2

        self.assertEqual([1, 1, 1, 1, 1, 1], store_001.children[storeproductunit_sku1].seller._sale_hist)
        self.assertEqual([2, 2, 2, 2, 2, 2], store_001.children[storeproductunit_sku2].seller._sale_hist)
        self.assertEqual([3, 3, 3, 3, 3, 3], store_001.children[storeproductunit_sku3].seller._sale_hist)

        env.step(None)
        # The demand in the data file should be added after env.step, and now it is filled with 0 if it is not implemented.
        self.assertEqual([1, 1, 1, 1, 1, 10], store_001.children[storeproductunit_sku1].seller._sale_hist)
        self.assertEqual([2, 2, 2, 2, 2, 100], store_001.children[storeproductunit_sku2].seller._sale_hist)
        self.assertEqual([3, 3, 3, 3, 3, 100], store_001.children[storeproductunit_sku3].seller._sale_hist)

        self.assertEqual(1, env.metrics["products"][26]["sale_mean"])
        self.assertEqual(43.0, env.metrics["products"][26]["selling_price"])

        self.assertEqual(3, env.metrics["products"][29]["sale_mean"])
        self.assertEqual(28.0, env.metrics["products"][29]["selling_price"])

        self.assertEqual(2, env.metrics["products"][32]["sale_mean"])
        self.assertEqual(17.0, env.metrics["products"][32]["selling_price"])

    def test_distribution_state_only(self) -> None:
        """Test the "pending_order" and "in_transit_orders" of the distribution unit."""
        env = build_env("case_05", 100)
        be = env.business_engine
        assert isinstance(be, SupplyChainBusinessEngine)

        supplier_3 = be.world._get_facility_by_name("Supplier_SKU3")
        distribution_unit = supplier_3.distribution
        warehouse_1 = be.world._get_facility_by_name("Warehouse_001")
        retailer_1: FacilityBase = be.world._get_facility_by_name("Retailer_001")
        consumer_unit = warehouse_1.products[3].consumer
        env.step(None)

        order = Order(warehouse_1, SKU3_ID, 20, "train")

        # There are 2 "train" in total, and 1 left after scheduling this order.
        consumer_unit._update_open_orders(warehouse_1, SKU3_ID, 20)
        distribution_unit.place_order(order)
        self.assertEqual(1, len(distribution_unit._order_queues["train"]))
        self.assertEqual(20, sum([order.quantity for order in distribution_unit._order_queues["train"]]))
        supplier_3_id, warehouse_1_id, retailer_1_id = 1, 6, 13

        env.step(None)

        # vlt is greater than len(pending_order_len), which will cause the pending order to increase
        self.assertEqual([0, 0, 20, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        # add another order, it would be successfully scheduled.
        order = Order(warehouse_1, SKU3_ID, 25, "train")
        consumer_unit._update_open_orders(warehouse_1, SKU3_ID, 25)
        distribution_unit.place_order(order)
        self.assertEqual(1, len(distribution_unit._order_queues["train"]))
        self.assertEqual(25, sum([order.quantity for order in distribution_unit._order_queues["train"]]))

        # 3rd order, will cause the pending order increase
        order_1 = Order(warehouse_1, SKU3_ID, 30, "train")
        consumer_unit._update_open_orders(warehouse_1, SKU3_ID, 30)
        distribution_unit.place_order(order_1)


        self.assertEqual(2, len(distribution_unit._order_queues["train"]))
        self.assertEqual(55, sum([order.quantity for order in distribution_unit._order_queues["train"]]))
        self.assertEqual(55, env.metrics["facilities"][supplier_3_id]["pending_order"][SKU3_ID])
        self.assertEqual(55, distribution_unit._pending_product_quantity[SKU3_ID])

        warehouse_1_distribution_unit = warehouse_1.distribution
        order_2 = Order(retailer_1, SKU3_ID, 5, "train")

        consumer_unit._update_open_orders(warehouse_1, SKU3_ID, 5)
        warehouse_1_distribution_unit.place_order(order_2)

        consumer_unit._update_open_orders(warehouse_1, SKU3_ID, 5)
        warehouse_1_distribution_unit.place_order(order_2)
        self.assertEqual(5+5, env.metrics["facilities"][warehouse_1_id]["pending_order"][SKU3_ID])
        self.assertEqual(5+5, warehouse_1_distribution_unit._pending_product_quantity[SKU3_ID])

        consumer_unit._update_open_orders(warehouse_1, SKU3_ID, 5)
        warehouse_1_distribution_unit.place_order(order_2)
        self.assertEqual(15, env.metrics["facilities"][warehouse_1_id]["pending_order"][SKU3_ID])
        self.assertEqual(15, warehouse_1_distribution_unit._pending_product_quantity[SKU3_ID])

        # There is no place_order for the distribution of supplier_3, there should be no change
        self.assertEqual(55, env.metrics["facilities"][supplier_3_id]["pending_order"][SKU3_ID])
        self.assertEqual(55, distribution_unit._pending_product_quantity[SKU3_ID])

        start_tick = env.tick
        expected_supplier_tick = start_tick + 3

        while env.tick < expected_supplier_tick - 1:
            env.step(None)

        self.assertEqual([20, 25, 0, 0], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        env.step(None)
        self.assertEqual([25, 0, 0, 30], list(env.metrics["facilities"][supplier_3_id]["pending_order_daily"][SKU3_ID]))

        # will arrive at the end of this tick, still on the way.
        assert env.tick == expected_supplier_tick
        self.assertEqual(0, len(distribution_unit._order_queues["train"]))
        self.assertEqual(0, sum([order.quantity for order in distribution_unit._order_queues["train"]]))
        self.assertEqual(5, env.metrics["facilities"][warehouse_1_id]["pending_order"][SKU3_ID])
        self.assertEqual(5, warehouse_1_distribution_unit._pending_product_quantity[SKU3_ID])

        env.step(None)

        self.assertEqual(0, len(distribution_unit._order_queues["train"]))
        self.assertEqual(0, sum([order.quantity for order in distribution_unit._order_queues["train"]]))
        self.assertEqual(45, env.metrics["facilities"][warehouse_1_id]["in_transit_orders"][SKU3_ID])

        self.assertEqual(5, env.metrics["facilities"][warehouse_1_id]["pending_order"][SKU3_ID])
        self.assertEqual(5, warehouse_1_distribution_unit._pending_product_quantity[SKU3_ID])


if __name__ == "__main__":
    unittest.main()
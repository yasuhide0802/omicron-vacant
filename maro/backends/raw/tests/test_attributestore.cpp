// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

#include "lest.hpp"
#include "../attributestore.h"


using namespace std;
using namespace maro::backends::raw;

const lest::test specification[] =
{
  CASE("Setup with specified size")
  {
    // TODO: fill later
  },

  CASE("Getter before any adding should cause exception.")
  {
    auto ats = AttributeStore();

    EXPECT_THROWS_AS(ats(0, 0, 0, 0), BadAttributeIndexing);
  },

  CASE("Getter should return reference of attribute.")
  {
    auto ats = AttributeStore();

    ats.setup(10);

    // add 1 node type 1 node, each node contains attribute 0 with 10 slots
    ats.add_nodes(0, 0, 1, 0, 10);

    EXPECT(10 == ats.last_index());

    // get 1st slot

    auto& attr = ats(0, 0, 0, 0);

    // get value
    // NOTE: this will change data type of attribute
    attr = -1;

    //
    EXPECT(-1 == attr.get_int());

    // get again to see if value changed
    EXPECT(-1 == ats(0, 0, 0, 0).get_int());


    // invalid index will cause exception
    EXPECT_THROWS_AS(ats(0, 0, 0, 11), BadAttributeIndexing);
  },

  CASE("Getter with invalid index or id will cause exception.")
  {
    auto ats = AttributeStore();

    ats.add_nodes(0, 0, 10, 0, 1);

    EXPECT(10 == ats.last_index());

    // get with invalid node index
    EXPECT_THROWS_AS(ats(0, 10, 0, 0), BadAttributeIndexing);

    // get with invalid node id
    EXPECT_THROWS_AS(ats(1, 0, 0, 0), BadAttributeIndexing);

    // get with invalid slot index
    EXPECT_THROWS_AS(ats(0, 0, 0, 1), BadAttributeIndexing);

    // get with invalid attribute id
    EXPECT_THROWS_AS(ats(0, 0, 1, 0), BadAttributeIndexing);
  },

  CASE("Add will extend the existing space.")
  {
    auto ats = AttributeStore();

    ats.setup(10);

    EXPECT(0 == ats.last_index());

    // add 1 node attribute
    ats.add_nodes(0, 0, 5, 0, 1);

    EXPECT(5 == ats.last_index());

    // size should be same as setup specified
    EXPECT(10 == ats.capacity());

    // actually only 5 slots being used.
    EXPECT(5 == ats.size());

    // 2nd attribute
    ats.add_nodes(0, 0, 5, 1, 1);

    EXPECT(10 == ats.last_index());

    // still within the capacity
    EXPECT(10 == ats.capacity());
    EXPECT(10 == ats.size());

    // this will extend internal space
    ats.add_nodes(0, 0, 5, 2, 10);

    // the size will be changed (double size of last_index)
    EXPECT(120 == ats.capacity());
    EXPECT(60 == ats.last_index());
    EXPECT(60 == ats.size());
  },

  CASE("Add without setup works same.")
  {
    auto ats = AttributeStore();

    ats.add_nodes(0, 0, 5, 0, 1);

    EXPECT(5 == ats.last_index());
    EXPECT(10 == ats.capacity());
    EXPECT(5 == ats.size());
  },

  CASE("Remove will cause empty slots in the middle of vector")
  {
    auto ats = AttributeStore();

    ats.setup(10);

    // add 1 attribute for node id 0, it will take 1st 6 slots
    ats.add_nodes(0, 0, 2, 0, 3);

    // set value for 2nd attribute of 1st node
    auto& attr = ats(0, 0, 0, 1);

    // update the value
    attr = 10;

    // remove 2nd node
    ats.remove_node(0, 1, 0, 3);

    // then getter for 2nd node should cause error
    EXPECT_THROWS_AS(ats(0, 1, 0, 1), BadAttributeIndexing);

    // but 1st node's attribute will not be affected.
    auto& attr2 = ats(0, 0, 0, 1);
    EXPECT(10 == attr2.get_int());
  },

  CASE("Remove with invalid parameter will not cause error.")
  {
    auto ats = AttributeStore();

    ats.add_nodes(0, 0, 1, 0, 10);

    // remove un-exist node_id
    EXPECT_NO_THROW(ats.remove_node(1, 0, 0, 10));

    // remove with invalid node index
    EXPECT_NO_THROW(ats.remove_node(0, 1, 0, 10));

    // remove with invalid attribute id
    EXPECT_NO_THROW(ats.remove_node(0, 0, 1, 10));

    // remove with invalid attribute slot number;
    EXPECT_NO_THROW(ats.remove_node(0, 0, 0, 20));
  },

  CASE("Arrange should fill empty slots with attribute at the end.")
  {
    auto ats = AttributeStore();

    
    ats.add_nodes(0, 0, 2, 0, 10);

    // after adding node attributes, last index should be 20
    EXPECT(20 == ats.last_index());

    // set value for last attribute of 2nd node
    auto& attr = ats(0, 1, 0, 9);

    attr = 10;

    // remove 1st node to gen empty slots
    ats.remove_node(0, 0, 0, 10);
   
    // arrange should work without exception
    EXPECT_NO_THROW(ats.arrange());
   
    // last index should be 10, as we will fill 10 empty slots
    EXPECT(10 == ats.last_index());

    // and our last node will be moved to 1st slot, but with updated index
    auto& attr2 = ats(0, 1, 0, 9);

    // so value should not be changed
    EXPECT(10 == attr2.get_int());

    // size will not change too
    
  },

    
  CASE("Last index should be at correct position after adding and removing.")
  {
    auto ats = AttributeStore();

    // add 2 node with 10 attribute per node
    ats.add_nodes(0, 0, 2, 0, 10);

    EXPECT(20 == ats.size());
    EXPECT(20 == ats.last_index());

    {
      // last attribute of 1st node after bellow removing operation
      auto& a = ats(0, 0, 0, 7);

      a = 100;

      auto& a2 = ats(0, 0, 0, 8);

      a2 = 110;
    }

    // case 1: narrow down attribute slots will cause last index changed
    ats.remove_attr_slots(0, 2, 0, 8, 10); // remove 8 and 9

    EXPECT_THROWS_AS(ats(0, 2, 0, 8), BadAttributeIndexing);

    // check last index
    EXPECT(16 == ats.size());
    EXPECT(20 == ats.last_index());

    ats.arrange();

    // we have remove 8th and 9th attribute for 2 nodes, so it has 4 empty slots totally
    EXPECT(16 == ats.size());
    EXPECT(16 == ats.last_index());

    // case 2: remove 2nd node will cause there are 8 empty slots at the end
    ats.remove_node(0, 1, 0, 8); // nodes have 8 attributes left

    // there should be 8 attributes left (1st node)
    EXPECT(8 == ats.size());

    // removing will not affect last index before arrange
    EXPECT(16 == ats.last_index());

    ats.arrange();

    // size should not change
    EXPECT(8 == ats.size());

    // last index will be updated
    EXPECT(8 == ats.last_index());

    // arrange will reset attributes that being removed, this should not affect exist, and new added will be 0 by default

    {
      auto& a = ats(0, 0, 0, 7);

      EXPECT(100 == a.get_int());
    }

    // add 4 additional slots
    ats.add_nodes(0, 0, 2, 0, 12);

    {
      auto& a = ats(0, 0, 0, 8);

      EXPECT(0 == a.get_int());
    }

    {
      auto& a = ats(0, 0, 0, 11);

      EXPECT(0 == a.get_int());
    }
  },

    CASE("COPY should not contain empty slot.")
  {
    auto ats = AttributeStore();

    ats.add_nodes(0, 0, 2, 0, 5);

    // set value for 1st & last attr of 2nd node, used to validate
    auto& attr = ats(0, 1, 0, 0);
    attr = 10;

    auto& attr2 = ats(0, 1, 0, 4);
    attr2 = 11;

    // remove node to gen empty slots
    ats.remove_node (0, 0, 0, 5);

    // target to hold attrs and map
    auto attrs_dest = vector<Attribute>(ats.size());
    auto map_dest = unordered_map<ULONG, size_t>();

    // no exception as we have enough space to hold attributes
    EXPECT_NO_THROW(ats.copy_to(&attrs_dest[0], &map_dest));

    // check if our attributes copied correct

    // 1st in destinition vector should be last one of 2nd node after arrange
    auto& attr3 = attrs_dest[0];

    EXPECT(11 == attr3.get_int());

    auto& attr4 = attrs_dest[attrs_dest.size() - 1];

    EXPECT(10 == attr4.get_int());

    // there should be 5 keys in map
    EXPECT(5 == map_dest.size());
  },

    CASE("Reset will clear internal states, but keep allocated memory to avoid furthur allocation.")
  {
    auto ats = AttributeStore();

    //
    ats.add_nodes(0, 0, 10, 0, 1);
    ats.add_nodes(0, 0, 5, 1, 1);

    ats.remove_node(0, 0, 0, 1);

    {
      auto& a = ats(0, 1, 0, 0);

      a = 111;
    }

    EXPECT(15 == ats.last_index());
    EXPECT(14 == ats.size());
    EXPECT(20 == ats.capacity());

    ats.reset();

    EXPECT(0 == ats.last_index());
    EXPECT(0 == ats.size());
    EXPECT(20 == ats.capacity());

    // NOTE: attributestore need to be setup again after reset
    EXPECT_THROWS_AS(ats(0, 1, 0, 0), BadAttributeIndexing);
  }
  
}
;
int main(int argc, char* argv[])
{
  return lest::run(specification, argc, argv);
}

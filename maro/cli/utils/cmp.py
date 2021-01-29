from maro.cli.grass.lib.services.utils.resource import BasicResource


def resource_op(node_resource: dict, container_resource: dict, op: str):
    if op == "release":
        updated_resource = {
            "cpu": node_resource["cpu"] + container_resource["cpu"],
            "memory": node_resource["memory"] + container_resource["memory"],
            "gpu": node_resource["gpu"] + container_resource["gpu"]
        }
        return True, updated_resource

    main_resource = BasicResource(
        cpu=node_resource["cpu"],
        memory=node_resource["memory"],
        gpu=node_resource["gpu"]
    )

    target_resource = BasicResource(
        cpu=container_resource["cpu"],
        memory=container_resource["memory"],
        gpu=container_resource["gpu"]
    )

    is_satisfied, updated_resource = True, {}
    if main_resource < target_resource:
        is_satisfied = False
    else:
        updated_resource = {
            "cpu": node_resource["cpu"] - container_resource["cpu"],
            "memory": node_resource["memory"] - container_resource["memory"],
            "gpu": node_resource["gpu"] - container_resource["gpu"]
        }

    return is_satisfied, updated_resource

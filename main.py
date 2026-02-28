import json
import subprocess

import yaml
import os
from collections import defaultdict

def load_dependency_graph(repo_root: str) -> dict:
    """
    Walks the monorepo, finds all service.yaml files,
    and returns a graph like:
    {
        "db-client": ["payments", "notifications"],
        "shared-utils": ["payments", "auth"]
    }
    """
    graph = {}
    for root, _, files in os.walk(repo_root):
        for file in files:
            full_file_path = os.path.join(root, file)
            if full_file_path.endswith("service.yaml"):
                with open(full_file_path, "r") as service:
                    data = yaml.safe_load(service)
                    graph[data["name"]] = data["dependencies"]
    return graph

def invert_graph(graph: dict) -> dict:
    inverted_graph = defaultdict(list)
    for key, value in graph.items():
        for item in value:
            inverted_graph[item].append(key)
    return dict(inverted_graph)

def get_changed_files():
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/master", "HEAD"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True, text=True
    )
    return result.stdout.strip().split("\n")

def get_affected_services(changed_files: list, inverted_graph: dict) -> set:
    """
    Given a list of changed file paths and the inverted dependency graph,
    return the set of services that need to be rebuilt.
    """
    affected_services = set()
    for file in changed_files:
        directory = os.path.dirname(file)
        split_directories = directory.split("/")
        if split_directories[0] == "services":
            affected_services.add(split_directories[-1])
        else:
            affected_services.update(inverted_graph.get(split_directories[-1], []))
    return affected_services

if __name__ == "__main__":
    try:
        graph = load_dependency_graph(".")
        inverted_graph = invert_graph(graph=graph)
        changed_files = get_changed_files()
        affected_services = get_affected_services(changed_files, inverted_graph)
        print(json.dumps(list(affected_services)))
    except Exception:
        print(json.dumps([]))
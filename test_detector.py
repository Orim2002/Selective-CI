from main import get_affected_services, load_dependency_graph, invert_graph

def test_get_affected_services_lib_change():
    changed_files = ["libs/db-client/client.py"]
    inverted_graph = {
        "db-client": ["payments", "notifications"],
        "shared-utils": ["payments", "auth"]
    }
    
    result = get_affected_services(changed_files, inverted_graph)
    assert result == {"payments", "notifications"}

def test_get_affected_services_service_change():
    changed_files = ["services/auth/auth.py"]
    inverted_graph = {
        "db-client": ["payments", "notifications"],
        "shared-utils": ["payments", "auth"]
    }
    result = get_affected_services(changed_files, inverted_graph)
    assert result == {"auth"}

def test_get_affected_services_no_dependents():
    changed_files = ["main.py"]
    inverted_graph = {
        "db-client": ["payments", "notifications"],
    }
    result = get_affected_services(changed_files, inverted_graph)
    assert result == set()

def test_load_dependency_graph(tmp_path):
    service_dir = tmp_path/"services"/"payments"
    service_dir.mkdir(parents=True)
    service_yaml = service_dir / "service.yaml"
    service_yaml.write_text(
    "name: payments\n"
    "dependencies:\n"
    "  - db-client\n"
    "  - shared-utils\n"
    )
    result = load_dependency_graph(tmp_path)
    assert result == {"payments": ["db-client", "shared-utils"]}


def test_invert_graph():
    graph = {
    "payments": ["db-client", "shared-utils"],
    "auth": ["shared-utils"],
    "notifications": ["db-client"]
    }
    result = invert_graph(graph)
    assert {key: set(value) for key, value in result.items()} == {
        "db-client": {"payments", "notifications"},
        "shared-utils": {"payments", "auth"}
    }

def test_load_dependency_graph_no_dependencies(tmp_path):
    service_dir = tmp_path / "services" / "auth"
    service_dir.mkdir(parents=True)
    service_yaml = service_dir / "service.yaml"
    service_yaml.write_text(
        "name: auth\n"
        "dependencies: []\n"
    )
    result = load_dependency_graph(tmp_path)
    assert result == {"auth": []}

def test_invert_graph_empty_dependencies():
    graph = {
        "auth": [],
        "payments": ["db-client"]
    }
    result = invert_graph(graph)
    assert {key: set(value) for key, value in result.items()} == {
        "db-client": {"payments"},
    }
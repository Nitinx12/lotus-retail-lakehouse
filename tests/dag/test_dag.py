# dag integrity tests for the airflow control plane
import ast
from itertools import pairwise
from pathlib import Path

import pytest

DAG_PATH = Path("dags/lotus_pipeline_dag.py")


# parses the dag source once for every structural check
def dag_tree() -> ast.Module:
    return ast.parse(DAG_PATH.read_text(encoding="utf-8"))


# collects task ids plus the keywords of the call that defines each one
def dag_tasks() -> dict[str, set[str]]:
    tasks: dict[str, set[str]] = {}
    for node in ast.walk(dag_tree()):
        if not isinstance(node, ast.Call):
            continue
        names = {kw.arg for kw in node.keywords if kw.arg}
        if "task_id" not in names:
            continue
        for kw in node.keywords:
            if kw.arg == "task_id" and isinstance(kw.value, ast.Constant):
                tasks[str(kw.value.value)] = names
    return tasks


# checks the dag file parses and defines the full section 2 flow
def test_dag_tasks_complete() -> None:
    tasks = dag_tasks()
    assert tasks, "no airflow tasks found"
    assert {
        "plpgsql_source_checks",
        "bronze",
        "gx_bronze",
        "silver",
        "gx_silver",
        "gold",
        "gx_gold",
        "jdbc_to_postgres",
        "plpgsql_gold_checks",
        "dbt",
        "r_analysis",
        "latex_report",
        "streamlit_refresh",
        "docker_build",
        "push",
    } <= set(tasks)


# checks every task carries an sla so overruns raise a miss
def test_dag_tasks_have_sla() -> None:
    assert [t for t, kw in dag_tasks().items() if "sla" not in kw] == []


# checks retries and the failure callback live in default args
def test_dag_default_args() -> None:
    for node in ast.walk(dag_tree()):
        if isinstance(node, ast.Call) and any(
            kw.arg == "default_args" for kw in node.keywords
        ):
            for kw in node.keywords:
                if kw.arg == "default_args" and isinstance(kw.value, ast.Dict):
                    keys = {
                        k.value for k in kw.value.keys if isinstance(k, ast.Constant)
                    }
                    assert "retries" in keys
                    assert "on_failure_callback" in keys
                    return
    raise AssertionError("default_args with retries and callback not found")


# checks sla misses route to the same alert callback
def test_dag_sla_miss_callback() -> None:
    found = any(
        isinstance(node, ast.Call)
        and any(kw.arg == "sla_miss_callback" for kw in node.keywords)
        for node in ast.walk(dag_tree())
    )
    assert found, "sla_miss_callback not registered"


# checks the dependency graph is acyclic and covers every task
def test_dag_graph_connected() -> None:
    tree = dag_tree()
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                for kw in node.value.keywords:
                    if kw.arg == "task_id" and isinstance(kw.value, ast.Constant):
                        names[target.id] = str(kw.value.value)
    edges: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.BinOp):
            chain: list[str] = []
            current: ast.AST = node.value
            while isinstance(current, ast.BinOp) and isinstance(current.op, ast.RShift):
                if isinstance(current.right, ast.Name):
                    chain.append(names.get(current.right.id, current.right.id))
                current = current.left
            if isinstance(current, ast.Name):
                chain.append(names.get(current.id, current.id))
            chain.reverse()
            edges.update(pairwise(chain))
    tasks = set(dag_tasks())
    assert tasks <= {n for edge in edges for n in edge}, "orphan tasks found"
    order: dict[str, int] = {}

    def visit(name: str, stack: set[str]) -> None:
        if name in stack:
            raise AssertionError(f"cycle at {name}")
        if name in order:
            return
        stack.add(name)
        for left, right in edges:
            if left == name:
                visit(right, stack)
        stack.remove(name)
        order[name] = len(order)

    for task in tasks:
        visit(task, set())


# checks environments resolve from a mapping not scattered conditionals
def test_dag_no_env_branching() -> None:
    for node in ast.walk(dag_tree()):
        if isinstance(node, ast.If):
            src = ast.unparse(node.test)
            assert "LOTUS_ENV" not in src, f"env branching found: {src}"
            assert "ENV_CONFIG" not in src


# checks the dag imports cleanly where airflow is installed
def test_dag_imports() -> None:
    pytest.importorskip("airflow")
    import importlib.util

    spec = importlib.util.spec_from_file_location("lotus_pipeline_dag", DAG_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {t.task_id for t in module.dag.tasks} == set(dag_tasks())

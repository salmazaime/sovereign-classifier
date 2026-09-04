# tests/test_k8s_parser.py
from pathlib import Path

from app.interceptor.iac.k8s_parser import parse_k8s_file


def test_pvc_with_declared_annotation_is_captured(tmp_path: Path):
    yaml_file = tmp_path / "pvc.yaml"
    yaml_file.write_text("""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: payroll-data
  namespace: hr
  annotations:
    sovereignty.acme.io/cloud: azure
    sovereignty.acme.io/region: francecentral
    sovereignty.acme.io/backing-bucket: hr-payroll-store
spec:
  storageClassName: encrypted-premium
""")
    resources = parse_k8s_file(yaml_file)
    assert len(resources) == 1
    assert resources[0].cloud_provider == "azure"
    assert resources[0].region == "francecentral"
    assert resources[0].encryption_enabled is True  # "encrypted" in storage class name


def test_pvc_without_annotation_is_skipped(tmp_path: Path):
    yaml_file = tmp_path / "pvc.yaml"
    yaml_file.write_text("""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: untracked-volume
spec:
  storageClassName: standard
""")
    resources = parse_k8s_file(yaml_file)
    assert resources == []


def test_configmap_with_sensitive_data_is_flagged(tmp_path: Path):
    yaml_file = tmp_path / "cm.yaml"
    yaml_file.write_text("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-fixtures
data:
  sample_user: "contact: jane@acme.com"
""")
    resources = parse_k8s_file(yaml_file)
    assert len(resources) == 1
    assert any(f["category"] == "ordinary_pii" for f in resources[0].content_findings)


def test_configmap_without_sensitive_data_is_not_created(tmp_path: Path):
    yaml_file = tmp_path / "cm.yaml"
    yaml_file.write_text("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: plain-config
data:
  log_level: "debug"
""")
    resources = parse_k8s_file(yaml_file)
    assert resources == []


def test_multi_document_file_and_irrelevant_kinds(tmp_path: Path):
    yaml_file = tmp_path / "multi.yaml"
    yaml_file.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: some-deployment
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tracked-pvc
  annotations:
    sovereignty.acme.io/cloud: aws
    sovereignty.acme.io/region: eu-west-3
spec: {}
""")
    resources = parse_k8s_file(yaml_file)
    assert len(resources) == 1
    assert resources[0].cloud_provider == "aws"
    
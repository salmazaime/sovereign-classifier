# tests/test_azure_blob_connector.py
from unittest.mock import MagicMock, patch

from app.connectors.azure.blob_connector import discover_blob_containers


@patch("app.connectors.azure.blob_connector.BlobServiceClient")
def test_discover_blob_containers_maps_account_and_container(mock_blob_service_cls):
    mock_factory = MagicMock()
    mock_storage_client = MagicMock()
    mock_factory.storage_client.return_value = mock_storage_client

    mock_account = MagicMock(
        name="teststorageacct", location="westeurope",
        id="/subscriptions/x/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/teststorageacct",
        minimum_tls_version="TLS1_2", allow_blob_public_access=False, tags={},
    )
    mock_storage_client.storage_accounts.list_by_resource_group.return_value = [mock_account]

    mock_container = MagicMock(name="mycontainer", public_access=None)
    mock_blob_service_instance = MagicMock()
    mock_blob_service_instance.list_containers.return_value = [mock_container]
    mock_container_client = MagicMock()
    mock_container_client.list_blobs.return_value = []
    mock_blob_service_instance.get_container_client.return_value = mock_container_client
    mock_blob_service_cls.return_value = mock_blob_service_instance

    resources = discover_blob_containers(mock_factory, resource_group="rg1")

    assert len(resources) == 1
    assert resources[0].resource_type == "azure_blob_container"
    assert resources[0].encryption_enabled is True  # always-on, per Azure's default

    
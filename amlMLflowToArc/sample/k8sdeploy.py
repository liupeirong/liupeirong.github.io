from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    KubernetesOnlineEndpoint,
    KubernetesOnlineDeployment,
    CodeConfiguration,
    Model,
    Environment)
from azure.ai.ml.exceptions import LocalEndpointNotFoundError
from azure.identity import DefaultAzureCredential

# connect to the workspace
subscription_id = 'mysub'
resource_group = 'myrg'
workspace = 'myws'
ml_client = MLClient(DefaultAzureCredential(), subscription_id, resource_group, workspace)

# create or get the endpoint
online_endpoint_name = "irisk8s-endpoint-local"
cpu_compute_target = "k3sedge4compute"
endpoint = KubernetesOnlineEndpoint(
    name=online_endpoint_name,
    compute=cpu_compute_target,
    description="this is a iris k3s endpoint",
    auth_mode="key",
)
try:
    endpoint = ml_client.online_endpoints.get(name=online_endpoint_name, local=True)
except LocalEndpointNotFoundError:
    endpoint = ml_client.online_endpoints.begin_create_or_update(endpoint, local=True)

# prepare model and env for deployment
# model = Model(path="model/model.lgb")
model = Model(path="model", type="mlflow_model")
# model = ml_client.models.get(name="iristutorialmodel", version="1")

env = Environment(
    conda_file="model/conda.yaml",
    image="mcr.microsoft.com/azureml/lightgbm-3.2-ubuntu18.04-py37-cpu-inference:20221107.v3",
    # image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:20221101.v1",
)

deployment = KubernetesOnlineDeployment(
    name="default",
    endpoint_name=online_endpoint_name,
    model=model,
    environment=env,
    code_configuration=CodeConfiguration(
        code="scoring/", scoring_script="score.py"
    ),
)

ml_client.online_deployments.begin_create_or_update(deployment, local=True)

print("Creating default deployment. Check the status in the Azure portal.")

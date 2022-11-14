#import required libraries
from azure.ai.ml import MLClient, command, Input
from azure.ai.ml.constants import ModelType
from azure.ai.ml.entities import Model, KubernetesOnlineEndpoint, KubernetesOnlineDeployment, CodeConfiguration
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import (
    ManagedOnlineEndpoint,
    ManagedOnlineDeployment,
    Model,
    Environment,
)
from azure.ai.ml.constants import ModelType 

#Enter details of your AzureML workspace
subscription_id = 'mysub'
resource_group = 'myrg'
workspace = 'myws'

#connect to the workspace
ml_client = MLClient(DefaultAzureCredential(), subscription_id, resource_group, workspace)

# specify aml compute name.
cpu_compute_target = "k3sedge4compute"   # "cpu-cluster"

try:
    ml_client.compute.get(cpu_compute_target)
except Exception:
    print ("kubernetes compute target not found, creating a new one")
    exit(1)
#     print("Creating a new cpu compute target...")
#     compute = AmlCompute(
#         name=cpu_compute_target, size="STANDARD_D2_V2", min_instances=0, max_instances=1
#     )
#     ml_client.compute.begin_create_or_update(compute).result()

# # define the command
# command_job = command(
#     code="./training",
#     command="python main.py --iris-csv ${{inputs.iris_csv}} --learning-rate ${{inputs.learning_rate}} --boosting ${{inputs.boosting}}",
#     environment="AzureML-lightgbm-3.2-ubuntu18.04-py37-cpu@latest",
#     inputs={
#         "iris_csv": Input(
#             type="uri_file",
#             path="https://azuremlexamples.blob.core.windows.net/datasets/iris.csv",
#         ),
#         "learning_rate": 0.9,
#         "boosting": "gbdt",
#     },
#     compute="cpu-cluster",
# )
# # submit the command
# returned_job = ml_client.jobs.create_or_update(command_job)
# # get a URL for the status of the job
# status_url = returned_job.services["Studio"].endpoint
# print(status_url)

# # register the model
registered_model_name = "iristutorial-model"

# run_model = Model(
#     path="azureml://jobs/{}/outputs/artifacts/paths/model/".format(returned_job.name),
#     name=registered_model_name,
#     description="Model created from run.",
#     type=ModelType.MLFLOW
# )

# ml_client.models.create_or_update(run_model)

# online_endpoint_name = "iristutorial-endpoint"
# create an online endpoint
# endpoint = ManagedOnlineEndpoint(
#     name=online_endpoint_name,
#     description="this is an iris tutorial online endpoint",
#     auth_mode="key",
# )

model = ml_client.models.get(name="iristutorialmodel", version="1")
#model = Model(path="model", type="mlflow_model")
#online_endpoint_name = "irisk8s-endpoint"
online_endpoint_name = "irisonline"

# online_endpoint_name = "irisk8s-endpoint"
# endpoint = KubernetesOnlineEndpoint(
#     name=online_endpoint_name,
#     compute=cpu_compute_target,
#     description="this is a iris k3s endpoint",
#     auth_mode="key",
# )
#endpoint = ml_client.online_endpoints.begin_create_or_update(endpoint, local=True)
#endpoint = ml_client.online_endpoints.get(name=online_endpoint_name, local=True)

endpoint = ml_client.online_endpoints.get(name=online_endpoint_name)

# env="AzureML-lightgbm-3.2-ubuntu18.04-py37-cpu@latest",
env = Environment(
    conda_file="model/conda.yaml",
    image="mcr.microsoft.com/azureml/lightgbm-3.2-ubuntu18.04-py37-cpu-inference:20221107.v3",
)

blue_deployment = KubernetesOnlineDeployment(
    name="blue",
    endpoint_name=online_endpoint_name,
    model=model,
    environment=env,
    app_insights_enabled=False,
    code_configuration=CodeConfiguration(
        code="scoring/", scoring_script="score.py"
    ),
    instance_count=1
)

# create an online deployment.
# blue_deployment = ManagedOnlineDeployment(
#     name="blue",
#     endpoint_name=online_endpoint_name,
#     model=model,
#     instance_type="Standard_DS3_v2",
#     instance_count=1,
# )

print("Creating blue deployment...")

result = ml_client.online_deployments.begin_create_or_update(blue_deployment)

# test the blue deployment with some sample data
# comment this out as cluster under dev subscription can't be accessed from public internet.
# result = ml_client.online_endpoints.invoke(
#    endpoint_name=online_endpoint_name,
#    deployment_name='blue',
#    request_file='./deploy/request.json')

result = ml_client.online_endpoints.invoke(
   endpoint_name=online_endpoint_name,
   request_file='.\\deploy\\request-local.json',
   local=True)

print(result)
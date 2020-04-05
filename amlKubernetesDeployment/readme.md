## How Azure Machine Learning Service deployment to Azure Kubernetes Service works

You can deploy machine learning models as a web service to Azure Kubernetes Service (AKS) programatically using Azureml Machine Learning Service Python SDK. In cases where the model is trained with AutoML, you can even deploy the model from Azure portal without writing any code. If everything works well, the deployment typically only takes a few minutes and the state of the target web service endpoint will transition to _healthy_, ready to receive inferencing requests. However when something goes wrong, the state of the endpoint will stay in _transitioning_ for a long time before it finally fails. Calling ```get_logs()``` on the service object does get you the container log running the service. But if the log message isn't clear, it's very hard to troubleshoot what went wrong. Here we will take a look at how the service deployment works so that you'll be more resourceful when it comes to troubleshooting.  

>*Note*: How Azure ML deploys a model can change without notice. This content only reflects the state as of Mar 2020. Also, for simplicity we are looking at a deployment to a dev/test AKS cluster with one worker node. Multi-node cluster deployment should be similar.

Using Azure Machine Learning Python SDK, you can deploy a web service to AKS as following:

```python
inference_env = Environment.from_conda_specification(name = "my_inference_env_name", file_path = "/path/to/my_inference_env.yml")
inference_config = InferenceConfig(source_directory = "/path/to/my/code", entry_script = "my_score.py", environment = inference_env)
aks_target = AksCompute(my_aml_workspace, "my_aks_compute_name")
deployment_config = AksWebservice.deploy_configuration(cpu_cores = 1, memory_gb = 2)
service = Model.deploy(my_aml_workspace, "myservicename", [my_model], inference_config, deployment_config, aks_target)
```

You can read up on how to create the model, the execution script, and the conda environment file in the [Azure ML documentation](https://docs.microsoft.com/en-us/azure/machine-learning/service/how-to-deploy-and-where). What's not in the documentation, however, is how everything is put together to run the scoring web service in AKS. 

This is what's happening behind the scene in the deployment:
1. Building a docker image for the inferencing environment.
    *  Every time you deploy, a docker image will be created in the Azure ML Workspace owned Azure Container Registry (ACR) for the inferencing environment. It's typically named ```azureml/azureml_{unique-id}```.
    *  This image has the dependent packages specified in the environment yaml file. But it doesn't have your model or code. 
    *  The log for building the image can be found in the Azure ML Workspace owned Azure Storage account in the blob container ```azureml```, under the path ```ImageLogs```.

2. Deploying to AKS.
    *  A persistent volume is created by mounting the Azure ML owned Storage container to the AKS node. This can be examined by issuing the following series of kubectl commands:

```bash
# find the namespace for Azure ML deployment, it starts with "azureml-"
kubectl get namespaces

# set the context to the Azure ML namespace 
kubectl config set-context --current --namespace=azureml-{myworkspace}

# get the pod running your service
kubectl get pod {myservicename}-{unique-string} -o yaml   
# it will show a persistent volume claim like this
#  volumes:
#  - name: staging
#    persistentVolumeClaim:
#      claimName: {myservicename}{unqiueid}-pvc
#      readOnly: true

# get the persistent volume and verify it's mounted to the "azureml" container of your Azure ML Storage account
kubectl get pv {myservicename}{unqiueid}-pvc -o yaml
# it will show the definition of the persistent volume like this:
# flexVolume:
#   driver: azure/blobfuse
#   options:
#     container: azureml
```

   *  Your code is located in the ```LocalUpload``` folder of the blob container, and your model is located in the ```ExperimentRun``` folder of the container. Exactly which files are used can be found with the following series of kubectl commands:

```bash
# get the deployment of your service
kubectl get deployment {myservicename} -o yaml
# it shows an environment variable called InitContainerConfig, find its definition as following:
kubectl describe configmaps {myservicename}{uniqueid}-config
# this will show the exact model files and code on the blob storage like this:
#    "Models": [
#        {
#            "{model_name}:{model_version}": [
#                {
#                    "Path": "ExperimentRun/dcid.{unique-id}/outputs/model.pkl",
#                    "Content": null,
#                    "ContainerPath": "./azureml-models/{model_name}/{model_version}/model.pkl",
#                    "UnpackType": 0
#                }
#            ]
#        },
#    ],
#    "Dependency": [
#        {
#            "Path": "LocalUpload/{unique-id}/tmp{unique-id}.py",
#            "Content": null,
#            "ContainerPath": "/main.py",
#            "UnpackType": 0
#        },
#        {
#            # this is a zip of your code folder
#            "Path": "LocalUpload/{unique-id}/{unique-id}.tar.gz",
#            ...
#        }
#    ],
#    "MountPath": "/var/azureml-app",
```

   *  The code will be mounted to ```/var/azureml-app```, and the models will be in ```/var/azureml-app/azureml-models```

With the code and models mounted, the inner workings of the pod is very similar to [how a single Azure ML docker image works](https://liupeirong.github.io/amlDockerImage/). The differences are:
*  Azure ML code is in ```/var/azureml-server```, while user code and models are in ```/var/azureml-app```. 
*  The port that Flask listens on is not 9090. In my case it's a port in the 30000 range.

The pod looks like this:
<img src="images/amlpod.png" alt="Azure Machine Learning Pod image" />

If you need to debug the pod running the Azure ML service or run the pod yourself, you can use kubectl to [interact with the pod](https://kubernetes.io/docs/reference/kubectl/cheatsheet/#interacting-with-running-pods), or you can [ssh into the AKS node](https://docs.microsoft.com/en-us/azure/aks/ssh). 

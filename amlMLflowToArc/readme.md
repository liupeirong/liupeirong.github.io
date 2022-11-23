# Azure Machine Learning v2: Deploy MLFlow model to Kubernetes

I have an Arc enabled Kubernetes cluster and would like to use Azure ML Python SDK v2 to deploy a model registered in Azure ML to the cluster.
 This turned out to be more involved than expected. It requires a good understanding of quite a few concepts, including the different model
 types that Azure ML supports, especially [MLFlow model](https://www.mlflow.org/docs/latest/models.html), no-code deployment, local deployment,
 managed vs. unmanaged endpoints, and the different capabilities of Azure ML SDK vs. Cli vs. portal in deployment.

This article explains a few lessons learned in deploying a MLFlow model to Arc enabled Kubernetes.
 Source code can be found in [this repo](https://github.com/liupeirong/amlv2_mlflow_to_kubernetes)

## Prepare your Kubernetes cluster

Whether you have an Arc enabled Kubernetes cluster or Azure Kubernetes cluster, the steps to set it up to connect to Azure ML are same. Follow

* [__Step 1__ to deploy Azure ML extension to your cluster](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-kubernetes-extension?tabs=deploy-extension-with-cli)
* [__Step 2__ to attach your cluster to an Azure ML workspace](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-attach-kubernetes-to-workspace?tabs=cli).

Completing these two steps is sufficient to deploy models to your cluster.
 The rest of the steps in [this doc](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-attach-kubernetes-anywhere) is optional.

## Train and register a model

If you follow the [Azure ML how-to guide to train and register a model](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-train-model?tabs=python),
 it may not be immediately obvious that this sample trains a [MLflow model](https://www.mlflow.org/docs/latest/models.html):

* The training script for this sample is located [here](https://github.com/Azure/azureml-examples/tree/main/sdk/python/jobs/single-step/lightgbm/iris/src).
* Sample code to connect to Azure ML and register the model is located [here](https://github.com/liupeirong/amlv2_mlflow_to_kubernetes/blob/main/main.py).

## Deploy the model

Now it's time to deploy the model. This could be confusing because the [Azure ML how-to guide to deploy a model](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-managed-online-endpoints?tabs=python) doesn't use the MLflow model trained above,
 but a scikit-learn model packaged as a `pkl`. To deploy, it requires a `score.py`. However, there's no `score.py`
 for our MLflow model because [scoring script for MLflow model is auto-generated for no-code deployment](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-mlflow-models?tabs=fromjob%2Cmir%2Csdk).

But no-code deployment of MLflow models works for managed endpoints, it doesn't for Kubernetes. At the time of this writing,
 [using Azure ML SDK v2 to deploy MLflow model to Kubernetes is not supported](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-mlflow-models?tabs=fromjob%2Cmir%2Csdk#deployment-tools). You can, however, write your own `score.py` and then deploy from Azure ML Studio portal.

There is no example of `score.py` for MLflow model, so how to write one? The `MLmodel` file in the MLflow model package describes
 [the input/output schema that the model expects](https://www.mlflow.org/docs/latest/models.html#model-signature-and-input-example).
 Note that the `score.py` you write is probably different from the one auto-generated, so the input data format may be different from
 what you provide to an Azure ML managed endpoint the model is deployed to.

Here's a sample [score.py](https://github.com/liupeirong/amlv2_mlflow_to_kubernetes/blob/main/scoring/score.py).

## Troubleshoot failed deployment

It's quite unlikely that your deployment of the MLflow model to your Kubernetes cluster succeeds at first try.
 Depending on where it fails, it may not even have helpful logs yet. So how do you troubleshoot?
 [Deploying the model locally](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-managed-online-endpoints?tabs=python#deploy-the-model-locally)
 in a docker container helps you to not only troubleshoot issues more effectively but also better understand how Azure ML works.

Wait, didn't we just say deploying MLflow model to unmanaged endpoints using the SDK is not supported?
 Isn't local endpoint unmanaged? Yes and yes. So we need to do some exploration. If we use the Python SDK to deploy the model locally with our `score.py`,
 here are some issues that you might see and tips on how to work around them.

* Model can't be mounted with an `OSError` exception on Windows `WinError 123`. Go to Azure ML Studio portal to download the registered model to a folder `model`.
 You need `conda.yaml` in the model package to set up your local and Kubernetes environment anyways.
* Even though the model contains the environment info it needs to run, if you don't specify the environment, you will get `RequiredLocalArtifactsNotFoundError`.
 Create an environment by picking a base docker image that matches your model and `conda.yaml` from the downloaded `model` folder.
* The downloaded `conda.yaml` doesn't include the [Inference Http Server](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-inference-server-http) required for inferencing in a local or Kubernetes deployment. You need to [add this package](https://github.com/liupeirong/amlv2_mlflow_to_kubernetes/blob/main/model/conda.yaml#L10).

Here's the [sample code for local deployment](https://github.com/liupeirong/amlv2_mlflow_to_kubernetes/blob/main/deploy_local.py).

Run the following command to verify local endpoint works:

```bash
curl -d "{\"data\":[[1,2,3,4]]}" -H "Content-Type: application/json" localhost:<port>/score
```

### Understand how deployment works

Take a look at the docker container by either `docker inspect <container-id>` or `docker exec -it <container-id> /bin/bash`. You will notice:

* Your model and code are mounted under `/var/azureml-app`
* Environment variables point to code and model artifacts:
  * `AZUREML_MODEL_DIR` points to the model folder
  * `AML_APP_ROOT` points to the code folder
  * `AZUREML_ENTRY_SCRIPT` points to the scoring script `score.py`

The code generated in `/var/azureml-server` and `/var/runit/gunicorn/run` leverages these environment variables to [run your code](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-inference-server-http#request-flow).

### Deploy to Kubernetes

Once local deployment succeeds, deploy to Kubernetes:

* from Azure ML Studio portal using the same `score.py`
* or, using Python SDK with the same `score.py`. Here's the [sample code for Kubernetes deployment](https://github.com/liupeirong/amlv2_mlflow_to_kubernetes/blob/main/deploy_kubernetes.py).

The model will be deployed to the Kubernetes
 [namespace you specified when you attached the cluster to Azure ML workspace](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-attach-kubernetes-to-workspace?tabs=studio#prerequisite).
 You can get the scoring endpoint and API key programmatically or from the portal.

Run the following command to verify Kubernetes endpoint works:

```bash
curl -d "{\"data\":[[1,2,3,4]]}" -H "Content-Type: application/json" -H "Authorization: Bearer <your key>" <your scoring url>
```

## Summary

While you need to have a basic understanding of the various concepts of Azure ML, MLflow, and Azure Arc enabled Kubernetes to get started,
Azure ML lets you centrally deploy ML models to Azure Arc enabled Kubernetes running anywhere in Azure, on-premises, or in other cloud.

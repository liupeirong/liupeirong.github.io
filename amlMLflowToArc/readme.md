# Azure Machine Learning v2: Deploy MLFlow model to Kubernetes

I have an Arc enabled Kubernetes cluster and would like to use Azure ML Python SDK v2 to deploy a model registered in Azure ML to the cluster.
This turned out to be more involved than expected. It requires a good understanding of quite a few concepts, including the different model
types that Azure ML supports, such as [MLFlow model](), local deployment, and the different capabilities of Azure ML SDK vs. Cli vs. portal in deployment.

This article explains some learns learned in deploying a MLFlow model to Arc enabled Kubernetes.

## Prepare your Kubernetes cluster

Whether you have an Arc enabled Kubernetes cluster or Azure Kubernetes cluster, the steps to set it up cluster to connect to Azure ML are same. Follow [__Step 1__ to deploy Azure ML extension to your cluster](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-kubernetes-extension?tabs=deploy-extension-with-cli) and [__Step 2__ to attach your cluster to an Azure ML workspace](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-attach-kubernetes-to-workspace?tabs=cli). Completing these two steps is sufficient to deploy models to your cluster. The rest of the steps in the doc is optional.

## Train and register a model

Next, you might follow the [Azure ML how-to guide to train and register a model](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-train-model?tabs=python). It may not be obvious that the training script for this sample is located [here](https://github.com/Azure/azureml-examples/tree/main/sdk/python/jobs/single-step/lightgbm/iris/src).

Note that this sample happens to be an [MLflow model](https://www.mlflow.org/docs/latest/models.html) which is a standard format for many model serving tools. It could be quite challenging to troubleshoot deployment issues without some basic understanding of MLflow models.  

Here's the example code for training and registration.

## Deploy the model

Now it's time to deploy the model. This could be confusing because the [Azure ML how-to guide to deploy a model](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-managed-online-endpoints?tabs=python) doesn't use the MLflow model trained above, but a scikit-learn model packaged as a `pkl`. To deploy, it requires a `score.py`. However, there's no `score.py` for our MLflow model because [scoring script for MLflow model is auto-generated](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-mlflow-models?tabs=fromjob%2Cmir%2Csdk).

So you might think you can do a no-code deployment of our MLflow model to the cluster. But that's true for managed endpoints, not true for Kubernetes. At the time of this writing, [using Azure ML SDK v2 to deploy MLflow model to Kubernetes is not supported](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-mlflow-models?tabs=fromjob%2Cmir%2Csdk#deployment-tools). You can, however, write your own `score.py` and then deploy from Azure ML Studio portal.

But, there is not an example of `score.py` for our MLflow model, how to write one? You can do so based on the `MLmodel` file in the MLflow model package which describes [the input/output schema that the model expects](https://www.mlflow.org/docs/latest/models.html#model-signature-and-input-example). Note that your `score.py` is probably different from the one auto-generated, so the input data format may be different from what you provide to a managed endpoint the model is deployed to.

## Troubleshoot failed deployment

It's quite unlikely that your deployment of the MLflow model to your Kubernetes cluster succeeds at first try. Depending on where it fails, it may not even have helpful logs yet. So how do you troubleshoot? [Deploying the model locally](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-managed-online-endpoints?tabs=python#deploy-the-model-locally) in a docker container helps you to not only troubleshoot issues more effectively but also understand how Azure ML works better.

But didn't we just say deploying MLflow model to unmanaged endpoints using the SDK is not supported? Isn't local endpoint unmanaged? Both are true. So we need to do some undocumented exploration. If we use the Python SDK to get the registered model and deploy locally with our `score.py`, here are the errors that we might see and how to work around them.

* Model can't be mounted with an `OSError` exception on Windows `WinError 123`. Go to Azure ML Studio portal to download the registered model in a folder `model`. The content should look like this:

TODO

* Even though the model contains the environment info it needs to run, if you don't specify the environment, you will get `RequiredLocalArtifactsNotFoundError`. Create an environment by picking a base docker image that matches your model and a conda file from the downloaded `model` folder. TODO: the conda file needs extra dependencies Inference Http Server!

Here's the full example of local deployment. Run the following code to verify everything works.

`curl -d "{\"data\":[[1,2,3,4]]}" -H "Content-Type: application/json" localhost:49205/score`

TODO: Inference Http Server

### Understanding how deployment works

Take a look at the docker container by either `docker inspect <container-id>` or `docker exec -it <container-id> /bin/bash`. You will see your model and code are mounted in `/var/azureml-app` with environment variables point to them:

* `AZUREML_MODEL_DIR` points to the model folder
* `AML_APP_ROOT` points to the code folder
* `AZUREML_ENTRY_SCRIPT` points to the scoring script

TODO: The code generated in `/var/azureml-server` and `/var/runit/gunicorn/run` leverages these variables to [run your code](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-inference-server-http#request-flow).

Once local deployment works, not only the same `score.py` can be used for Kubernetes deployment from the portal, but you can even use the same workaround to deploy MLflow model using Python SDK. The model will be deployed to the Kubernetes namespace you specified when you connected the cluster to Azure ML workspace(TODO). You can get the scoring endpoint and key programmatically or from the portal and run the following command to verify it works.

`curl -d '{"data":[[1,2,3,4]]}' -H "Content-Type: application/json" -H "Authorization: Bearer key" -X POST http://10.0.0.4:30130/api/v1/endpoint/irisonline/score`


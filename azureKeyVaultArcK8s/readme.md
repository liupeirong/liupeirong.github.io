# Overview

[Azure Key Vault Secrets Provider extension](https://learn.microsoft.com/en-us/azure/azure-arc/kubernetes/tutorial-akv-secrets-provider) in Azure Arc lets you store secrets in Azure Key Vault and fetch them to your Kubernetes cluster. The benefits of this include the following:

* Kubernetes secrets are not encrypted. It's more secure to store secrets in Azure Key Vault.
* The secrets can also be [automatically rotated](https://learn.microsoft.com/en-us/azure/azure-arc/kubernetes/tutorial-akv-secrets-provider#additional-configuration-options).

Limitations:

* You still need to configure a Service Principle that can access Key Vault, and store it as a secret in Kubernetes to fetch other secrets.
* When the cluster is disconnected from the cloud, existing pods using Azure Key Vault secrets will continue to run, however, they will not be able to restart until connection to the cloud is restored.
* If you enable sync as Kubernetes secret, a Kubernetes secret will be created for each mounted Azure Key Vault secret. As long as there is at least one pod with mounted Azure Key Vault secret running, other pods could use the synced Kubernetes secret without any knowledge of Key Vault. However, if the last pod using Key Vault is deleted, the synced secret is also deleted. The pods using the synced secret will continue to run, but will not be able to restart.

## How does it work

[This tutorial](https://learn.microsoft.com/en-us/azure/azure-arc/kubernetes/tutorial-akv-secrets-provider#additional-configuration-options) details how to use this Arc extension. Here are the basic steps:

1. Install the extension

```bash
az k8s-extension create --cluster-name $CLUSTER_NAME --resource-group $RESOURCE_GROUP --cluster-type connectedClusters --extension-type Microsoft.AzureKeyVaultSecretsProvider --name akvsecretsprovider
```

If you want to enable sync as Kubernetes secret, as shown in this example, run the following instead:

```bash
# to install the extension
az k8s-extension create --cluster-name $CLUSTER_NAME --resource-group $RESOURCE_GROUP --cluster-type connectedClusters --extension-type Microsoft.AzureKeyVaultSecretsProvider --name akvsecretsprovider secrets-store-csi-driver.syncSecret.enabled=true

# to update an already installed extension
az k8s-extension update --cluster-name $CLUSTER_NAME --resource-group $RESOURCE_GROUP --cluster-type connectedClusters --name akvsecretsprovider --configuration-settings secrets-store-csi-driver.syncSecret.enabled=true
```

The extension is installed for the cluster. Everything below is configured for a Kubernetes namespace.

2. [Provide credential](sample/akvCreds.yaml) to your Kubernetes cluster to access Azure Key Vault
1. [Deploy a SecretProviderClass](sample/secretProviderClass.yaml) to specify which secrets to fetch from Azure Key Vault. The sample demonstrates secrets and certificates. Detailed yaml syntax on the SecretProviderClass can be found in the [Secret Store CSI Driver doc](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret.html). 
1. [Deploy a pod that mounts the secrets](sample/busyboxDeployment.yaml).
1. Validate the secrets are indeed mounted, and synced Kubernetes secrets are created:

```bash
kubectl exec -it <busybox-pod> -n <namespace> -- ls /mnt/secrets
kubectl get secrets -n <namespace>
```

You can also deploy [another pod that uses synced Kubernetes secrets](sample/busyboxDeploymentKS.yaml). However, if you delete the first busybox pod, and restart this second pod by running `kubectl rollout restart deployment busyboxks`, it can't start because the synced secrets are deleted.

In summary, this feature is great for externalizing secrets to a secure vault, but it's not for scenarios when the cluster needs to deploy or restart pods when disconnected from the cloud.

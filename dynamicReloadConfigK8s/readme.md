# Reload dotnet core configuration without restarting Kubernetes pod

In general it's a good practice to design micro services to be stateless so that they can fully benefit from the power of Kubernetes to remain resilient and highly available. Sometimes, however, making a configuration change without restarting the pod is ideal. For example, if you are troubleshooting a service that only fails occasionally, it'll be nice to make logging more verbose without restarting the service because restarting the service could mean the failure condition goes away for a while. In this article, we'll take a look at how to change logging level in dotnet core applications without restarting the pod the app is running in.

Dotnet core already supports `reloadOnChange` for configuration files. The challenge with running in Kubernetes is that when ConfigMap changes, the file points to a symlink, so its last write time doesn't change, the target of the symlink changes. [Dotnet core 6 added support for symlink change detection](https://github.com/dotnet/runtime/pull/55664).

## Add a configuration file that can be reloaded on change

1. Create a folder dedicated for dynamic configuration files. The reason for this is that Kubernetes ConfigMap can be mounted as a file rather than a folder using `subPath`. However, a container using a ConfigMap as a [subPath volume will not receive ConfigMap updates in Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/#mounted-configmaps-are-updated-automatically).

2. Load a configuration file in the folder created above with `reloadOnChange`. For example:

```c#
var builder = WebApplication.CreateBuilder(args);
builder.Host.ConfigureAppConfiguration((hostingContext, config) =>
{
    config.AddJsonFile("dynamic-config/settings.json", optional: true, reloadOnChange: true);
});
```

3. When you build the docker image for the application, add an environment variable `ENV DOTNET_USE_POLLING_FILE_WATCHER true` because the symlink support in dotnet core [uses polling file watcher](https://learn.microsoft.com/en-us/dotnet/api/microsoft.extensions.fileproviders.physicalfileprovider.usepollingfilewatcher?view=dotnet-plat-ext-6.0).

## Create ConfigMap in Kubernetes

1. Create a ConfigMap in Kubernetes, and mount it to the app container. As mentioned above, it needs to be mounted as a folder not a `subPath`. For example,

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-dynamic-config
data:
  settings.json: |
    {
      "Logging": {
        "LogLevel": {
          "Default": "Warning"
        }
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: myapp-container
        image: myapp:1.0
        volumeMounts:
          - mountPath: /app/dynamic-config
            name: dynamic-config-vol
      volumes:
        - name: dynamic-config-vol
          configMap:
            name: my-dynamic-config
```

2. When you need to change the logging level, update and reapply the ConfigMap. For example, to change the logging level to `Debug`,

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-dynamic-config
data:
  settings.json: |
    {
      "Logging": {
        "LogLevel": {
          "Default": "Debug"
        }
      }
    }
```

If you use `Kustomize`, you can apply this change as a patch. It will replace the file `/app/dynamic-config/settings.json`.
However, don't create this ConfigMap with `ConfigMapGenerator`, because  `ConfigMapGenerator` adds the hash of its content as suffix of the ConfigMap name. If the content changes, it's a new ConfigMap that the Container points to, which means the deployment will be automatically updated and the pod restarted.

Although this article uses logging as an example, you could use the same mechanism combined with dotnet core IOptions pattern to reload other app configurations.

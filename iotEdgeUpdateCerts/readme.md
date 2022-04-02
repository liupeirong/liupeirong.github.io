# How to update expired certificates on Azure IoT Nested Edge

If you use X.509 certificates to establish trust between Azure IoT Edge devices and IoT Hub, or between child and parent devices in nested edge scenarios, updating the certificates manually is a non-trivial task and also could cause downtime. This is because the certificate thumbprint of an IoT Edge device cannot be updated once registered. This article describes the manual processes for updating certificates in the Azure IoT Nested Edge scenario with one parent device that connects to Azure IoT Hub and one child device that doesn't have Internet access.

<img src="media/nested_edge_overview.png" />

## Step 1: Prepare new certificates
Similar to provisioning a new nested edge environment, the following certificates are needed:
* identity certificate and key for edge4 to authenticate to IoT Hub
* identity certificate and key for edge3 to authenticate to IoT Hub through edge4
* edge CA certificate and key for edge3 to trust its parent edge4
* root CA certificate that's used to sign other certificates if it needs update

If you name these certificates exactly the same as existing certificates and place them in the same folders on both edge devices, then you don't need to change the IoT Edge configuration files `/etc/aziot/config.toml`.

## Step 2: Remove old certificates from edge devices
On each edge device:

1. Stop IoT Edge `sudo iotedge system stop`.
2. Delete existing certificates:
```bash
sudo rm -rf /var/lib/aziot/certd/certs
sudo rm -rf /var/lib/aziot/keyd/keys
```
3. Take a backup of the following files:
  * `/etc/aziot/config.toml`
  * If you use a custom Nginx configuration file mounted to IoTEdgeAPIProxy module for nested edge, take a backup of that file. 
4. Purge and reinstall IoT Edge. On the edge device with no Internet connection, you need another way to reinstall.
```bash
sudo apt-get remove --purge aziot-identity-service
sudo apt-get remove --purge aziot-edge
sudo apt-get update
sudo apt-get install aziot-edge
```

## Step 3: Install new certificates
On each edge device:

1. If root CA certificate is updates, copy and trust the new root CA certificate, for example, 
```bash
sudo cp /path/to/ca_cert.pem /usr/local/share/ca-certificates/ca_cert.pem.crt
sudo update-ca-certificates
```
2. Copy and replace the identity cert in the same location as before
3. On the parent edge, copy and replace the edge CA certificates in the same location as before. 
4. Take a backup of the deployment manifest of the edge device.
5. Delete the edge device from IoT Hub.
6. Re-register the edge device in IoT Hub with its new identity certificate thumbprint.
```bash
# retrieve thumbprint from certificate
openssl x509 -in /path/to/identity_cert.pem -text -fingerprint | sed 's/[:]//g'
```
7. Copy the iotedge config file from Step 2.3 to `/etc/aziot/config.toml`.
8.  Start iotedge ```sudo iotedge system apply```. 

After a minute or so, you should see the parent edge successfully registered with IoT Hub.

## Step 4: Re-deploy modules to the parent edge
1.  At this point, the parent edge is registered, but if you were using a custom Nginx config file, it might be deleted when IoTEdge was removed. Stop IoTEdge to restore this file before deploying modules.
```bash
sudo iotedge system stop
sudo docker rm IoTEdgeAPIProxy
```
2. Copy the custom Nginx config file from Step 2.3 to the original location to be mounted to IoTEdgeAPIProxy module, making sure it's accessbile by the module. 
```bash
sudo mkdir /path/to/proxyconf
sudo chmod 755 /path/to/proxyconf
sudo cp /path/to/backup/defult.conf /path/to/proxyconf/default.conf
sudo chmod 644 /path/to/proxyconf/default.conf
```
3. Restart IoTEdge and deploy modules using the deployment manifest saved at Step 3.4:
```bash
sudo iotedge system restart
az iot edge set-modules --hub-name {iothub_name} --device-id {device_id} --content {/path/to/deployment_manifest.json}
```

After a minute or so, you should see the child edge successfully registered with IoT Hub.

## Step 5: Re-deploy modules to the child edge
At this point, the child edge is successfully registered with IoT Hub, however, some modules on the child edge might still be failing because the containers might be holding on to the state of the old certificates.

1. Delete the docker containers for the modules that failed to start:
```bash
sudo iotedge system stop
# sudo docker rm <containers that failed to start>
sudo iotedge system restart
```
2. Restart IoTEdge and deploy modules using the deployment manifest saved at Step 3.4:
```bash
sudo iotedge system restart
az iot edge set-modules --hub-name {iothub_name} --device-id {device_id} --content {/path/to/deployment_manifest.json}
```

## Summary
Updating expired or to-be-expired certificates in nested edge scenarios is an involved process. Invest in automation to manage such environment at scale and reduce downtime.

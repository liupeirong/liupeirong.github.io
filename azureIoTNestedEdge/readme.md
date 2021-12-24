# Lessons learned from setting up Azure IoT Nested Edge with X.509 Certificates

Manufacturing customers often run their workload on the factory floor in networks that follow ISA-95 standard - machines on the lower layer don't have Internet access and can only communicate with the machines a layer directly above. Azure IoT Edge supports connecting a hierarchy of edge devices with the downstream devices in an isolated network connecting to a top layer edge device acting as a gateway. Additionally, manufacturing customers often have strict security requirements that only allow for CA signed certificate based authentication.

[Tutorial: Create a hierarchy of IoT Edge devices](https://docs.microsoft.com/en-us/azure/iot-edge/tutorial-nested-iot-edge?view=iotedge-2020-11) uses the `iotedge-config` tool to automatically provision and configure the devices. Not being an IoT expert, I wanted to manually provision and configure a nested edge scenario, using CA signed certificates for authentication where possible, so I can better understand how it works. I ran into a few issues where no readily available answers can be found on the Internet, and decided to write them up here.

## What are we trying to build?

The goal is to create 2 edge devices, one in a subnet with Internet access (the gateway edge device), and another in an isolated subnet that doesn't have Internet access. Configure them such that we can see their status in Azure IoT Hub as if they are both connected to IoT Hub, and the messages sent from the edge modules on the network isolated edge device can go through the gateway edge device to IoT Hub.

<img src="images/overview.png" />

Here are the main steps to build this out in Azure:

1. Create a VNET with 2 subnets, layer3 and layer4.
2. Create 2 Ubuntu VMs, edge3 in layer3 subnet and edge4 in layer4 subnet. [Install Azure IoT Edge on both machines](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-provision-single-device-linux-symmetric?view=iotedge-2020-11&tabs=azure-portal#install-iot-edge). Here we only install the bits, not registering the devices to Azure.
3. Add a NSG to layer3 subnet that denies all inbound and outbound Internet connection. Verify that edge3 can no longer 'curl' any public web site.
4. [Generate demo certificates](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-create-test-certificates?view=iotedge-2020-11). Note that for nested edge to work, the edge hostname used for registering devices must be FQDN or IP. The CN in the certificates must match the hostnames.
5. Use Azure IoT Device Provisioning Service (DPS) to provision edge4 with the generated certificates.
6. Authenticate and connect edge3 using the generated certificates as the child of edge4.
7. Deploy the simulated temperature module to edge3 and verify the messages are received in IoT Hub.

## What did I learn?

All the above steps are straightforward except step 6. The following are some of the key learnings from trying to make it work.

[Provision IoT Edge device at scale using X.509 certificates](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-provision-devices-at-scale-linux-x509?view=iotedge-2020-11&tabs=individual-enrollment) finally documents how to use CA signed certificates for authentication with Azure IoT Device Provisioning Service. However, in [Authenticate a downstream device], it stated "Automatic provisioning downstream devices with the Azure IoT Hub Device Provisioning Service (DPS) is not supported."
[Configure gateways for IoT Edge devices](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-connect-downstream-iot-edge-device?view=iotedge-2020-11&tabs=azure-portal) focuses on configure the parent-child relatioship rather than how to authenticate the lower layer edge device.

### Register the downstream edge in IoT Hub without Internet connection

The document [Configure gateways for IoT Edge devices](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-connect-downstream-iot-edge-device?view=iotedge-2020-11&tabs=azure-portal) assumes both downstream and top layer edges are already registered, and therefore focuses on configuring the parent-child relatioship. [Authenticate a downstream device to Azure IoT Hub](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-authenticate-downstream-device?view=iotedge-2020-11) only applies to non-edge downstream IoT devices. So how to register the downstream edge when it can't connect to the Internet?

Even to register the top layer edge, [Provision a single IoT Edge device using X.509 certificates](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-provision-single-device-linux-x509?view=iotedge-2020-11&tabs=azure-portal) only talks about X.509 _self-signed_ rather than _CA-signed_ certificate for authentication, which is consistent with the "Add an Edge device" capability in the Azure Portal. We have a CA-signed certificate. So we follow [Provision IoT Edge device at scale using X.509 certificates](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-provision-devices-at-scale-linux-x509?view=iotedge-2020-11&tabs=individual-enrollment) to provision the top layer edge. It's important to note -

* use the "full-chain" identity certificate for DPS.
* DPS doesn't support provisioning downstream devices. But provisioning the top layer edge with DPS is fine.
* when you later deploy the required modules to the top layer edge, it will complain about 'iothub_hostname' unknown. DPS knows which IoT Hub it connects to, but it seems that the modules may not know. In the /etc/aziot/config.toml, under the section of DPS provisioning, add a line to specify 'iothub_hostname'.

With the top layer edge provisioned and registered, follow [Configure a transparent gateway](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-create-transparent-gateway?view=iotedge-2020-11) to configure it as a gateway.

[Deploy the necessary modules to the top layer edge](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-connect-downstream-iot-edge-device?view=iotedge-2020-11&tabs=azure-portal#deploy-modules-to-top-layer-devices) so it can support the downstream edges. If everything is correctly configured, you should be able to verify the following from the downstream device:

* `curl https://<topLevelFQDN>/v2/_catalog` returns an array of docker images in your container registry.
* `docker pull <topLevelFQDN>/<a_docker_image>` correctly pulls the image. Note that if you don't sepcify a FQDN or IP, by default docker will try to pull from docker hub which will fail because the downstream device doesn't have Internet access.

Copy the root certificate to the downstream edge and trust it.

```bash
sudo cp <path>/<root ca certificate>.pem /usr/local/share/ca-certificates/<root ca certificate>.pem.crt
sudo update-ca-certificates
```

Register the IoT Edge as self-signed cert. Then configure parent/child relationship in IoT Hub

Modify the downstream edge device's /etc/aziot/config.toml to use manual provisioning with X.509:

```yaml
## Manual provisioning with X.509 certificate
[provisioning]
source = "manual"
iothub_hostname = "<myhub>.azure-devices.net"
device_id = "<this-device-FQDN>"

[provisioning.authentication]
method = "x509"

## identity certificate private key
identity_pk = "file:///path/to/iot-edge-device-identity-<name>.key.pem"

## identity certificate
identity_cert = "file:///path/to/iot-edge-device-identity-<name>-full-chain.cert.pem"

##
[agent]
name = "edgeAgent"
type = "docker"

[agent.config]
image: "<parent-FQDN>:443/azureiotedge-agent:<version 1.2 or above>"
```

Apply the configuration by running `sudo iotedge config apply`. Verify the downstream edge is successfully registered in IoT Hub.

### FQDN and name resolution

The FQDN for the edge hostname must be resolvable not just from the host machines of both edge devices, but also from inside docker containers. This means if the hostnames are added to the hosts' /etc/hosts, then they must be added as docker containers' create options. In /etc/aziot/config.toml, this means the edge agent must be configured as following:

```yaml
[agent.config]
image: "<parent-FQDN>:443/azureiotedge-agent:<version 1.2 or above>"
createOptions = { HostConfig = { ExtraHosts=["<FQDN_child>:<IP_child>", "<FQDN_parent>:<IP_parent>"], Binds = ["/iotedge/storage:/iotedge/storage"] } }
```

If you initially run the edge agent without this setting on the downstream edge, and add it later, it won't be updated unless you `docker rm` the existing edge agent container and rerun `iotedge config apply`. You can use `docker inspect edgeAgent` to verify it does have the `ExtraHosts` set correctly.

In IoT Hub, the deployment manifest should include the following for the modules' create options:

```json
{
    "HostConfig": {
        "ExtraHosts": [
            "<FQDN_child>:<IP_child>",
            "<FQDN_parent>:<IP_parent>"
        ],
        "Binds": [
            "/iotedge/storage:/iotedge/storage"
        ]
    }
}
```

### Required certificates and their respective use

In IoT Hub or DPS, you need the root CA certificate (public), so that the Hub will only register devices signed by this certificate.

In the gateway IoT Edge, you need

1. root CA cert to trust (public)
2. identity cert (both public and private)
3. edge CA cert (both public and private)

In the leaf IoT Edge, you need

1. root CA cert to trust (public)
2. identity cert (both public and private)

* How does downstream edge trust gateway edge? Downstream edge trust the root cert, gateway edge proves it has a private key for the edge CA cert.
* How does the gateway edge trust the downstream edge? Parent/Child relationship is set in IoT Hub, gateway edge trusts the root cert, the downstream edge proves it has a private key for its identity cert.
* How does IoT Hub trust the gateway edge? IoT Hub only respond to registered devices, to register, you must prove ownership of the root CA cert, the gateway edge proves it has a private key for its identity cert.
* How does the gateway edge trust IoT Hub? IoT Hub has CA signed certs for its endpoints and proves it has a private key. Gateway edge trusts the CA just like a browser trusts CA signed public web site.

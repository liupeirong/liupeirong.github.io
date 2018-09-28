## Connect MQTT Client to Azure IoT Hub

You can connect to Azure IoTHub using a generic MQTT client for testing.  I tried some online MQTT clients without success.  But [MQTTBox](http://workswithweb.com/html/mqttbox/downloads.html) works perfectly. 

Here's what you need to do: 
1.  Register a device in Azure IoTHub:
   
![Alt text](/mqttIOTHub/images/01adddevice.png?raw=true "Register a device")

2.  Download [Azure IoTHub Device Explorer](https://github.com/Azure/azure-iot-sdk-csharp/tree/master/tools/DeviceExplorer#download-a-pre-built-version-of-the-device-explorer-application) and [connect it to your IoTHub](https://github.com/Azure/azure-iot-sdk-csharp/tree/master/tools/DeviceExplorer#configure-an-iot-hub-connection). Generate an access token for the device to connect to IoTHub.  Copy everthing from `SharedAccessSignature=` as shown below:

![Alt text](/mqttIOTHub/images/02generatesas.png?raw=true "Generate SAS token")

3.  Download [MQTTBox](http://workswithweb.com/html/mqttbox/downloads.html), and set up connection to Azure IoTHub using websocket as shown below.  Note that 
    -  __Host__ should be appeneded with `/$iothub/websocket`
    -  __Username__ should be in the format `{your_iothub_name}.azure-devices.net/{your_device_id}/api-version=2016-11-14`
    -  __Password__ should be the SAS token you copied from the previous step. 
  
4.  Set up Device Explorer to monitor messages from IoTHub as documented [here](https://github.com/Azure/azure-iot-sdk-csharp/tree/master/tools/DeviceExplorer#monitor-device-to-cloud-events).
    
5.  Send a message from MQTTBox, and observe it from Device Explorer.  Note that the topic must be in the format `devices/{your_device_id}/messages/events/{your_property_name1}={value1}&{your_property_name2}={value2}...`.  The properties you put in the topic can be used for IoTHub message routing described [here](https://github.com/Azure/azure-iot-sdk-csharp/tree/master/tools/DeviceExplorer#monitor-device-to-cloud-events). 

![Alt text](/mqttIOTHub/images/03sendmessage.png?raw=true "Send message")
![Alt text](/mqttIOTHub/images/04monitormessage.png?raw=true "Monitor message")
